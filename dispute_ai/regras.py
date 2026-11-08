"""Modo demonstração: análise por regras, sem uso de API de LLM.

Usa expressões regulares e palavras-chave para extrair dados, classificar documentos e
identificar o motivo da contestação. É útil para testes, apresentações e como contingência
quando nenhuma chave de API está disponível. Imagens não são lidas neste modo (sem OCR).
"""

from __future__ import annotations

import re
import unicodedata

from .catalogo import rotulo_tipo
from .extracao import DocumentoCarregado
from .formatacao import moeda


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparação de palavras-chave."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


# ---------------------------------------------------------------------------
# Extração de campos
# ---------------------------------------------------------------------------
RE_VALOR = re.compile(r"R\$\s*([\d]{1,3}(?:\.\d{3})*,\d{2})")
RE_DATA = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
RE_CARTAO = re.compile(r"(?:\*{2,}|x{2,}|final\s*:?\s*)\s*(\d{4})\b", re.IGNORECASE)
RE_NSU = re.compile(r"\bNSU\s*[:\-]?\s*(\d{4,})", re.IGNORECASE)
RE_AUTORIZACAO = re.compile(
    r"(?:c[óo]d(?:igo)?\.?\s*(?:de\s*)?autoriza[çc][ãa]o|\bAUT\b)\s*[:\-]?\s*([A-Z0-9]{4,})",
    re.IGNORECASE,
)
RE_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
RE_CODIGO_MOTIVO = re.compile(
    r"(?:c[óo]digo\s+(?:do\s+)?motivo|reason\s+code)\s*[:\-]?\s*([\w\.]+)", re.IGNORECASE
)
RE_PRAZO = re.compile(r"prazo[^\n]{0,80}?(\d{2}/\d{2}/\d{4})", re.IGNORECASE)
# Rótulo seguido de ":" (texto livre) ou de quebra de linha (células de tabela em PDFs).
RE_ROTULO = r"\b{rotulo}\s*:\s*([^\n]{{2,80}})"
RE_ROTULO_QUEBRA = r"^[ \t]*{rotulo}[ \t]*:?[ \t]*\n[ \t]*([^\n]{{2,80}})"
RE_3DS_AUSENTE = re.compile(
    r"3-?d\s?s(?:ecure)?[^\n]{0,40}?\b(nao|n/a|ausente|sem|inexistente|nao realizad)", re.IGNORECASE
)

BANDEIRAS = ["VISA", "MASTERCARD", "ELO", "AMERICAN EXPRESS", "AMEX", "HIPERCARD"]


def valor_para_float(valor: str) -> float:
    return float(valor.replace(".", "").replace(",", "."))


def _primeiro(regex: re.Pattern, texto: str) -> str | None:
    m = regex.search(texto)
    return m.group(1).strip() if m else None


def _por_rotulo(texto: str, *rotulos: str, quebra: bool = True) -> str | None:
    """Busca o valor associado a um rótulo ("Rótulo: valor" ou "Rótulo\nvalor")."""
    padroes = [RE_ROTULO] + ([RE_ROTULO_QUEBRA] if quebra else [])
    for rotulo in rotulos:
        for padrao in padroes:
            m = re.search(padrao.format(rotulo=rotulo), texto, re.IGNORECASE | re.MULTILINE)
            if m:
                return m.group(1).strip()
    return None


def _data_transacao(texto: str) -> str | None:
    """Prefere datas rotuladas como da transação; senão, a primeira data do texto."""
    rotulada = _por_rotulo(texto, r"data da transa[çc][ãa]o", r"data/hora(?: \(utc-3\))?",
                           r"data de emiss[ãa]o", "data")
    if rotulada:
        m = RE_DATA.search(rotulada)
        if m:
            return m.group(1)
    return _primeiro(RE_DATA, texto)


def extrair_campos(texto: str) -> dict:
    """Extrai campos estruturados de um texto livre."""
    valores = [valor_para_float(v) for v in RE_VALOR.findall(texto)]
    valores = [v for v in valores if v > 0]
    bandeira = next((b for b in BANDEIRAS if re.search(rf"\b{b}\b", texto, re.IGNORECASE)), None)
    m_cnpj = RE_CNPJ.search(texto)
    campos = {
        "valor": max(valores) if valores else None,
        "valores_encontrados": sorted(set(valores)),
        "data": _data_transacao(texto),
        "cartao_final": _primeiro(RE_CARTAO, texto),
        "nsu": _primeiro(RE_NSU, texto),
        "codigo_autorizacao": _primeiro(RE_AUTORIZACAO, texto),
        "cnpj": m_cnpj.group(0) if m_cnpj else None,
        "bandeira": bandeira.title() if bandeira else None,
        "estabelecimento": _por_rotulo(texto, "estabelecimento", "loja", r"raz[ãa]o social", "emitente"),
        "titular": _por_rotulo(texto, "titular", "portador", "cliente", r"destinat[áa]rio", "comprador"),
        "produto": _por_rotulo(texto, "produto", r"descri[çc][ãa]o do produto", quebra=False),
        "canal": _por_rotulo(texto, "canal", "modalidade"),
    }
    return {k: v for k, v in campos.items() if v not in (None, [], "")}


# ---------------------------------------------------------------------------
# Classificação de documentos
# ---------------------------------------------------------------------------
PALAVRAS_TIPO: dict[str, list[str]] = {
    "notificacao_contestacao": ["notificacao de contestacao", "chargeback", "contestacao", "disputa",
                                "reason code", "codigo do motivo", "prazo para"],
    "nota_fiscal": ["nota fiscal", "nf-e", "nfe", "danfe", "chave de acesso"],
    "comprovante_entrega": ["comprovante de entrega", "rastreio", "rastreamento", "entregue em",
                            "recebedor", "transportadora", "aviso de recebimento"],
    "registro_transacao": ["registro da transacao", "log", "gateway", "nsu", "codigo de autorizacao",
                           "id da transacao", "adquirente"],
    "comprovante_pagamento": ["comprovante de pagamento", "recibo", "via do cliente",
                              "pagamento aprovado", "comprovante"],
    "autenticacao_3ds": ["3ds", "3-d secure", "autenticacao do portador", "fingerprint", "device id"],
    "comunicacao_cliente": ["atendimento", "chat", "prezado", "ola", "mensagem", "e-mail", "assunto:"],
    "politica_cancelamento": ["politica de cancelamento", "trocas e devolucoes", "politica de troca"],
    "comprovante_reembolso": ["estorno", "reembolso efetuado", "comprovante de reembolso"],
    "contrato_termos": ["termos de uso", "termos e condicoes", "contrato"],
}


def classificar_documento(doc: DocumentoCarregado) -> str:
    nome = normalizar(doc.nome.replace("_", " ").replace("-", " "))
    texto = normalizar(doc.texto[:6000])
    pontuacao: dict[str, float] = {}
    for tipo, palavras in PALAVRAS_TIPO.items():
        p = 0.0
        for palavra in palavras:
            if palavra in nome:
                p += 5
            p += min(texto.count(palavra), 3)
        pontuacao[tipo] = p
    if doc.nome.lower().endswith(".eml"):
        pontuacao["comunicacao_cliente"] += 4
    melhor = max(pontuacao, key=pontuacao.get)
    return melhor if pontuacao[melhor] > 0 else "outro"


# ---------------------------------------------------------------------------
# Motivo da contestação
# ---------------------------------------------------------------------------
PALAVRAS_MOTIVO: dict[str, list[str]] = {
    "nao_reconhecida": ["nao reconhec", "desconhec", "fraude", "nao autoriz", "10.4"],
    "nao_recebido": ["nao recebid", "nao entregue", "nao chegou", "13.1"],
    "divergente": ["defeito", "divergente", "diferente do anunciado", "13.3"],
    "cancelamento": ["cancelamento", "cancelad", "reembolso nao", "13.7"],
    "duplicidade": ["duplicidade", "cobrado duas vezes", "em dobro", "12.6"],
    "valor_incorreto": ["valor incorreto", "valor diferente", "12.5"],
}


def identificar_motivo(docs: list[DocumentoCarregado], tipos: dict[str, str]) -> dict:
    """Identifica o motivo, priorizando a notificação de contestação."""
    principais = [d for d in docs if tipos.get(d.nome) == "notificacao_contestacao"]
    base = principais or docs
    texto_original = "\n".join(d.texto for d in base)
    texto = normalizar(texto_original)

    pontuacao = {m: sum(texto.count(p) for p in palavras) for m, palavras in PALAVRAS_MOTIVO.items()}
    categoria = max(pontuacao, key=pontuacao.get)
    if pontuacao[categoria] == 0:
        categoria = "outro"

    descricao = _por_rotulo(texto_original, "motivo informado", "motivo da contestacao",
                            r"motivo da contesta[çc][ãa]o", "motivo")
    return {
        "categoria": categoria,
        "descricao": descricao,
        "codigo": _primeiro(RE_CODIGO_MOTIVO, texto_original),
        "prazo_resposta": _primeiro(RE_PRAZO, texto_original),
    }


# ---------------------------------------------------------------------------
# Análise completa (modo demonstração)
# ---------------------------------------------------------------------------
RESUMOS_TIPO = {
    "comprovante_pagamento": "Comprova a efetivação do pagamento.",
    "registro_transacao": "Registra os dados técnicos da autorização da transação.",
    "nota_fiscal": "Documento fiscal que vincula a cobrança a uma venda.",
    "comprovante_entrega": "Comprova a entrega do produto.",
    "comunicacao_cliente": "Registro de comunicação com o cliente.",
    "notificacao_contestacao": "Notificação formal da contestação com motivo e prazo.",
    "autenticacao_3ds": "Dados de autenticação do portador/dispositivo.",
    "politica_cancelamento": "Regras de cancelamento e devolução.",
    "comprovante_reembolso": "Comprova estorno ou reembolso.",
    "contrato_termos": "Termos aceitos pelo cliente.",
    "outro": "Documento sem classificação específica.",
}


def analisar_por_regras(docs: list[DocumentoCarregado]) -> dict:
    tipos = {d.nome: classificar_documento(d) for d in docs}
    motivo = identificar_motivo(docs, tipos)

    documentos, evidencias, pontos, inconsistencias = [], [], [], []
    campos_por_doc: dict[str, dict] = {}
    for d in docs:
        campos = extrair_campos(d.texto) if d.texto else {}
        campos_por_doc[d.nome] = campos
        tipo = tipos[d.nome]
        documentos.append({
            "arquivo": d.nome,
            "tipo": tipo,
            "resumo": RESUMOS_TIPO[tipo] if d.texto else
            "Imagem não lida no modo demonstração (classificada pelo nome do arquivo).",
            "dados_extraidos": {k: v for k, v in campos.items() if k != "valores_encontrados"},
        })
        if tipo not in ("outro", "notificacao_contestacao"):
            evidencias.append({
                "descricao": rotulo_tipo(tipo),
                "arquivo": d.nome,
                "forca": "moderada" if d.texto else "fraca",
            })
        if d.imagens and not d.texto:
            pontos.append(f"O arquivo '{d.nome}' é uma imagem e não foi lido no modo demonstração; "
                          "use um provedor de LLM com visão para extrair seu conteúdo.")

    # Consolida os dados da transação (prioridade: registro > comprovante > nota > demais).
    prioridade = ["registro_transacao", "comprovante_pagamento", "nota_fiscal",
                  "notificacao_contestacao", "comunicacao_cliente"]
    ordenados = sorted(docs, key=lambda d: prioridade.index(tipos[d.nome])
                       if tipos[d.nome] in prioridade else 99)
    transacao: dict = {}
    for d in ordenados:
        for k, v in campos_por_doc[d.nome].items():
            if k != "valores_encontrados":
                transacao.setdefault(k, v)

    # Verificações cruzadas.
    valores_principais = {c["valor"] for c in campos_por_doc.values() if c.get("valor")}
    if len(valores_principais) > 1:
        lista = ", ".join(moeda(v) for v in sorted(valores_principais))
        inconsistencias.append(f"Valores divergentes entre documentos: {lista}.")
    cartoes = {c["cartao_final"] for c in campos_por_doc.values() if c.get("cartao_final")}
    if len(cartoes) > 1:
        inconsistencias.append(f"Finais de cartão divergentes entre documentos: {', '.join(sorted(cartoes))}.")

    texto_total = normalizar("\n".join(d.texto for d in docs))
    if RE_3DS_AUSENTE.search(texto_total):
        pontos.append("A transação não possui autenticação 3DS, o que enfraquece a defesa em casos de fraude.")
    if "registro_transacao" in tipos.values():
        pontos.append("Necessidade de verificar os dados da transação (NSU, autorização, data e hora) "
                      "na base do adquirente.")

    return {
        "resumo": "",  # preenchido pelo analisador após avaliar o checklist
        "transacao": transacao,
        "motivo": motivo,
        "documentos": documentos,
        "evidencias": evidencias,
        "pontos_atencao": pontos,
        "inconsistencias": inconsistencias,
        "nivel_risco": None,
        "status": None,
        "recomendacao": "",
        "providencias": [],
    }
