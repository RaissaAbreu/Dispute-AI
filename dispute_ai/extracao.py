"""Extração de conteúdo dos documentos enviados (PDF, TXT, E-mail e imagens).

- PDF: texto via PyMuPDF; páginas sem texto (digitalizadas) são renderizadas como imagem
  para que um LLM com visão possa lê-las.
- TXT: decodificação com detecção simples de codificação.
- EML: cabeçalhos + corpo do e-mail; anexos de imagem/PDF também são aproveitados.
- Imagens: enviadas ao LLM com visão (no modo demonstração não há OCR local).
"""

from __future__ import annotations

import email
import hashlib
import html
import re
from dataclasses import dataclass, field
from email import policy

import pymupdf

from .config import (
    MAX_PAGINAS_IMAGEM_POR_PDF,
    MIN_CARACTERES_PAGINA_TEXTO,
    TIPOS_ACEITOS,
)


@dataclass
class Imagem:
    mime: str
    dados: bytes
    origem: str  # ex.: "página 2" ou nome do anexo


@dataclass
class DocumentoCarregado:
    nome: str
    mime: str
    dados: bytes
    texto: str = ""
    imagens: list[Imagem] = field(default_factory=list)
    paginas: int = 0
    metodo: str = ""
    avisos: list[str] = field(default_factory=list)

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.dados).hexdigest()

    @property
    def tamanho_kb(self) -> float:
        return round(len(self.dados) / 1024, 1)


class FormatoNaoSuportado(ValueError):
    pass


def extensao(nome: str) -> str:
    return nome.rsplit(".", 1)[-1].lower() if "." in nome else ""


def _decodificar_texto(dados: bytes) -> str:
    for cod in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return dados.decode(cod)
        except UnicodeDecodeError:
            continue
    return dados.decode("utf-8", errors="replace")


def _html_para_texto(conteudo: str) -> str:
    conteudo = re.sub(r"(?is)<(script|style).*?</\1>", " ", conteudo)
    conteudo = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", conteudo)
    conteudo = re.sub(r"<[^>]+>", " ", conteudo)
    conteudo = html.unescape(conteudo)
    return re.sub(r"[ \t]+", " ", conteudo).strip()


def _extrair_pdf(doc: DocumentoCarregado) -> None:
    try:
        pdf = pymupdf.open(stream=doc.dados, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise FormatoNaoSuportado(f"PDF inválido ou corrompido: {exc}") from exc

    if pdf.needs_pass:
        raise FormatoNaoSuportado("PDF protegido por senha.")

    doc.paginas = pdf.page_count
    partes: list[str] = []
    digitalizadas = 0
    for i, pagina in enumerate(pdf, start=1):
        texto = pagina.get_text("text").strip()
        if len(texto) >= MIN_CARACTERES_PAGINA_TEXTO:
            partes.append(f"[Página {i}]\n{texto}")
        else:
            digitalizadas += 1
            if len(doc.imagens) < MAX_PAGINAS_IMAGEM_POR_PDF:
                pix = pagina.get_pixmap(dpi=150)
                doc.imagens.append(Imagem("image/png", pix.tobytes("png"), f"página {i}"))
    pdf.close()

    doc.texto = "\n\n".join(partes)
    if digitalizadas and not partes:
        doc.metodo = "PDF digitalizado (imagem)"
        doc.avisos.append("PDF sem camada de texto: leitura depende de um LLM com visão.")
    elif digitalizadas:
        doc.metodo = "PDF misto (texto + imagem)"
        doc.avisos.append(f"{digitalizadas} página(s) sem texto foram convertidas em imagem.")
    else:
        doc.metodo = "PDF com texto (PyMuPDF)"


def _extrair_eml(doc: DocumentoCarregado) -> None:
    msg = email.message_from_bytes(doc.dados, policy=policy.default)
    cabecalhos = [
        f"De: {msg.get('From', '')}",
        f"Para: {msg.get('To', '')}",
        f"Data: {msg.get('Date', '')}",
        f"Assunto: {msg.get('Subject', '')}",
    ]
    corpo_txt, corpo_html, anexos = [], [], []
    for parte in msg.walk():
        if parte.is_multipart():
            continue
        tipo = parte.get_content_type()
        nome_anexo = parte.get_filename()
        if nome_anexo:
            anexos.append(nome_anexo)
            conteudo = parte.get_payload(decode=True) or b""
            if tipo.startswith("image/"):
                doc.imagens.append(Imagem(tipo, conteudo, f"anexo {nome_anexo}"))
            elif tipo == "application/pdf":
                sub = DocumentoCarregado(nome_anexo, tipo, conteudo)
                try:
                    _extrair_pdf(sub)
                    corpo_txt.append(f"\n[Anexo PDF: {nome_anexo}]\n{sub.texto}")
                    doc.imagens.extend(sub.imagens)
                except FormatoNaoSuportado as exc:
                    doc.avisos.append(f"Anexo {nome_anexo}: {exc}")
            continue
        if tipo == "text/plain":
            corpo_txt.append(parte.get_content())
        elif tipo == "text/html":
            corpo_html.append(_html_para_texto(parte.get_content()))

    corpo = "\n".join(corpo_txt) if corpo_txt else "\n".join(corpo_html)
    if anexos:
        cabecalhos.append("Anexos: " + ", ".join(anexos))
    doc.texto = "\n".join(cabecalhos) + "\n\n" + corpo.strip()
    doc.paginas = 1
    doc.metodo = "E-mail (.eml)"


def carregar_documento(nome: str, dados: bytes) -> DocumentoCarregado:
    """Lê um arquivo enviado e devolve seu conteúdo estruturado."""
    ext = extensao(nome)
    if ext not in TIPOS_ACEITOS:
        raise FormatoNaoSuportado(f"Formato .{ext or '?'} não suportado.")
    if not dados:
        raise FormatoNaoSuportado("Arquivo vazio.")

    doc = DocumentoCarregado(nome=nome, mime=TIPOS_ACEITOS[ext], dados=dados)

    if ext == "pdf":
        _extrair_pdf(doc)
    elif ext == "eml":
        _extrair_eml(doc)
    elif ext == "txt":
        doc.texto = _decodificar_texto(dados).strip()
        doc.paginas = 1
        doc.metodo = "Texto (.txt)"
    else:
        try:
            pix = pymupdf.Pixmap(dados)
            doc.avisos.append(f"Imagem {pix.width}×{pix.height}px — leitura via LLM com visão.")
        except Exception as exc:  # noqa: BLE001
            raise FormatoNaoSuportado(f"Imagem inválida: {exc}") from exc
        doc.imagens.append(Imagem(doc.mime, dados, "imagem enviada"))
        doc.paginas = 1
        doc.metodo = "Imagem"

    if not doc.texto and not doc.imagens:
        doc.avisos.append("Nenhum conteúdo legível foi encontrado.")
    return doc
