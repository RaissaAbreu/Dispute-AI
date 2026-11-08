"""Orquestra a análise de um caso: LLM (ou regras) + checklist determinístico + normalização."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

from .catalogo import MOTIVOS, NIVEIS_RISCO, STATUS, TIPOS_DOCUMENTO, avaliar_checklist, rotulo_motivo
from .config import MAX_CARACTERES_POR_DOCUMENTO, PROVEDORES
from .extracao import DocumentoCarregado
from .formatacao import moeda
from .llm import ErroLLM, Parte, gerar_resposta
from .llm.prompts import SISTEMA, cabecalho_documento, instrucao_final
from .regras import analisar_por_regras, normalizar

AVISO_LEGAL = ("Análise preliminar gerada automaticamente para apoio à decisão. "
               "Não substitui a avaliação de um analista humano.")


# ---------------------------------------------------------------------------
# Chamada ao LLM
# ---------------------------------------------------------------------------
def montar_partes(docs: list[DocumentoCarregado], observacoes: str) -> list[Parte]:
    partes = [Parte("texto", texto=f"Caso com {len(docs)} documento(s) recebido(s).")]
    for i, d in enumerate(docs, start=1):
        bloco = cabecalho_documento(i, d.nome, d.metodo)
        if d.texto:
            texto = d.texto
            if len(texto) > MAX_CARACTERES_POR_DOCUMENTO:
                texto = texto[:MAX_CARACTERES_POR_DOCUMENTO] + "\n[... conteúdo truncado ...]"
            bloco += texto
        if d.imagens:
            bloco += f"\n[{len(d.imagens)} imagem(ns) deste documento a seguir]"
        partes.append(Parte("texto", texto=bloco))
        for img in d.imagens:
            partes.append(Parte("texto", texto=f"Imagem de '{d.nome}' ({img.origem}):"))
            partes.append(Parte("imagem", mime=img.mime, dados=img.dados))
    partes.append(Parte("texto", texto=instrucao_final(observacoes)))
    return partes


def extrair_json(texto: str) -> dict:
    """Interpreta a resposta do modelo, tolerando cercas de markdown e texto ao redor."""
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ErroLLM("A resposta do modelo não contém um JSON válido.")
    try:
        return json.loads(texto[inicio:fim + 1])
    except json.JSONDecodeError as exc:
        raise ErroLLM(f"Não foi possível interpretar o JSON retornado pelo modelo: {exc}") from exc


# ---------------------------------------------------------------------------
# Normalização e enriquecimento
# ---------------------------------------------------------------------------
def _lista_str(valor) -> list[str]:
    if not valor:
        return []
    if isinstance(valor, str):
        return [valor]
    return [str(v).strip() for v in valor if str(v).strip()]


def _para_float(valor) -> float | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    s = re.sub(r"[^\d,.\-]", "", str(valor))
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _ja_mencionado(rotulo: str, pontos: list[str]) -> bool:
    alvo = normalizar(rotulo)
    return any(alvo in normalizar(p) for p in pontos)


def normalizar_analise(bruta: dict, docs: list[DocumentoCarregado]) -> dict:
    """Garante estrutura completa, valida enums e aplica o checklist determinístico."""
    a = dict(bruta or {})

    # Transação
    transacao = dict(a.get("transacao") or {})
    transacao["valor"] = _para_float(transacao.get("valor"))
    a["transacao"] = {k: v for k, v in transacao.items() if v not in (None, "", [])}

    # Motivo
    motivo = dict(a.get("motivo") or {})
    if motivo.get("categoria") not in MOTIVOS:
        motivo["categoria"] = "outro"
    motivo["rotulo"] = rotulo_motivo(motivo["categoria"])
    if not motivo.get("descricao"):
        motivo["descricao"] = motivo["rotulo"]
    a["motivo"] = motivo

    # Documentos: casa o retorno com os arquivos realmente enviados.
    por_nome = {str(d.get("arquivo", "")).strip(): d for d in (a.get("documentos") or [])
                if isinstance(d, dict)}
    documentos = []
    for d in docs:
        info = dict(por_nome.get(d.nome) or {})
        tipo = info.get("tipo") if info.get("tipo") in TIPOS_DOCUMENTO else "outro"
        documentos.append({
            "arquivo": d.nome,
            "tipo": tipo,
            "resumo": info.get("resumo") or "Documento não classificado pelo modelo.",
            "dados_extraidos": info.get("dados_extraidos") or {},
            "metodo": d.metodo,
            "paginas": d.paginas,
            "tamanho_kb": d.tamanho_kb,
            "avisos": d.avisos,
        })
    a["documentos"] = documentos

    a["evidencias"] = [e for e in (a.get("evidencias") or []) if isinstance(e, dict) and e.get("descricao")]
    for e in a["evidencias"]:
        if e.get("forca") not in ("forte", "moderada", "fraca"):
            e["forca"] = "moderada"
    a["pontos_atencao"] = _lista_str(a.get("pontos_atencao"))
    a["inconsistencias"] = _lista_str(a.get("inconsistencias"))
    a["providencias"] = _lista_str(a.get("providencias"))

    # Checklist determinístico
    tipos_presentes = {d["tipo"] for d in documentos}
    checklist = avaliar_checklist(motivo["categoria"], tipos_presentes)
    a["checklist"] = checklist
    a["documentos_ausentes"] = [
        {"documento": i["documento"], "obrigatorio": i["obrigatorio"], "justificativa": i["justificativa"]}
        for i in checklist["ausentes_obrigatorios"] + checklist["ausentes_recomendados"]
    ]

    faltam = checklist["ausentes_obrigatorios"]
    for item in faltam:
        if not _ja_mencionado(item["documento"], a["pontos_atencao"]):
            a["pontos_atencao"].insert(0, f"Ausência de {item['documento'].lower()}.")
    if faltam and not any("suficiente" in normalizar(p) for p in a["pontos_atencao"]):
        a["pontos_atencao"].append("Não há elementos suficientes para concluir sobre a legitimidade da compra.")

    # Status e risco: o checklist impede "suficiente" quando faltam obrigatórios.
    status = a.get("status")
    if status not in STATUS:
        status = None
    if status is None:
        if checklist["cobertura"] < 50:
            status = "insuficiente"
        elif faltam or a["inconsistencias"]:
            status = "revisao"
        else:
            status = "suficiente"
    elif status == "suficiente" and (faltam or a["inconsistencias"]):
        status = "revisao"
    a["status"] = status
    a["status_rotulo"] = STATUS[status]

    risco = a.get("nivel_risco")
    if risco not in NIVEIS_RISCO:
        tipos_faltantes = {i["tipo"] for i in faltam}
        if checklist["cobertura"] < 50 or ("comprovante_entrega" in tipos_faltantes
                                           and motivo["categoria"] in ("nao_reconhecida", "nao_recebido")):
            risco = "alto"
        elif faltam or a["inconsistencias"]:
            risco = "medio"
        else:
            risco = "baixo"
    a["nivel_risco"] = risco
    a["nivel_risco_rotulo"] = NIVEIS_RISCO[risco]

    # Recomendação e providências padrão, quando ausentes.
    if not a.get("recomendacao"):
        if status == "suficiente":
            a["recomendacao"] = ("Evidências compatíveis com o motivo informado: preparar a defesa "
                                 "e submeter à validação de um analista humano.")
        else:
            a["recomendacao"] = ("Solicitar documentação complementar e encaminhar para análise humana.")
    if not a["providencias"]:
        a["providencias"] = [f"Solicitar ao estabelecimento: {i['documento'].lower()}." for i in faltam]
        if motivo.get("prazo_resposta"):
            a["providencias"].append(f"Apresentar a resposta até {motivo['prazo_resposta']}.")
        a["providencias"].append("Encaminhar o caso para análise humana antes da resposta final.")

    if not a.get("resumo"):
        valor = a["transacao"].get("valor")
        valor_txt = moeda(valor) if valor else "valor não identificado"
        a["resumo"] = (f"Contestação de {valor_txt} com motivo \"{motivo['rotulo'].lower()}\". "
                       f"Foram recebidos {len(docs)} documento(s), cobrindo {checklist['cobertura']}% "
                       f"das evidências obrigatórias para este motivo.")
    a["aviso_legal"] = AVISO_LEGAL
    return a


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------
def analisar_caso(
    docs: list[DocumentoCarregado],
    provedor: str,
    modelo: str,
    chave_api: str = "",
    observacoes: str = "",
    fallback_demo: bool = True,
) -> dict:
    """Executa a análise completa e devolve o dicionário normalizado."""
    if not docs:
        raise ValueError("Nenhum documento informado.")

    inicio = time.perf_counter()
    meta = {"provedor": provedor, "provedor_nome": PROVEDORES[provedor].nome, "modelo": modelo,
            "modo": "demo" if provedor == "demo" else "llm", "fallback": None}

    if provedor == "demo":
        bruta = analisar_por_regras(docs)
    else:
        try:
            resposta = gerar_resposta(provedor, chave_api, modelo, SISTEMA, montar_partes(docs, observacoes))
            bruta = extrair_json(resposta)
        except ErroLLM as exc:
            if not fallback_demo:
                raise
            bruta = analisar_por_regras(docs)
            meta.update(modo="demo", fallback=str(exc), modelo="regras-v1",
                        provedor="demo", provedor_nome=PROVEDORES["demo"].nome)

    analise = normalizar_analise(bruta, docs)
    meta["duracao_s"] = round(time.perf_counter() - inicio, 2)
    meta["gerado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    analise["meta"] = meta
    analise["observacoes"] = observacoes
    return analise
