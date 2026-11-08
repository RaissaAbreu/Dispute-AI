"""Componentes visuais reutilizáveis: cabeçalhos, cartões e relatório de análise de um caso."""

from __future__ import annotations

import json
from html import escape

import pandas as pd
import streamlit as st

from .. import banco
from ..catalogo import rotulo_tipo
from ..config import PROVEDORES
from ..formatacao import moeda, rotulo_campo, valor_campo
from ..relatorio import gerar_pdf

CLASSE_STATUS = {"revisao": "vermelho", "insuficiente": "vermelho", "suficiente": "verde"}
CLASSE_DECISAO = {"pendente": "neutro", "defender": "azul", "aceitar": "verde", "aguardando_docs": "ambar"}
CLASSE_FORCA = {"forte": "verde", "moderada": "azul", "fraca": "neutro"}
CLASSE_RISCO = {"alto": "vermelho", "medio": "ambar", "baixo": "verde"}


def html(conteudo: str) -> None:
    """Renderiza HTML (remove indentação para não virar bloco de código no Markdown)."""
    st.markdown("".join(linha.strip() for linha in conteudo.splitlines()), unsafe_allow_html=True)


def pill(texto: str, classe: str = "neutro") -> str:
    return f"<span class='pill {classe}'>{escape(texto)}</span>"


# ---------------------------------------------------------------------------
# Cabeçalhos
# ---------------------------------------------------------------------------
def _pill_ia() -> str:
    cfg = st.session_state.get("config_llm", {})
    provedor = cfg.get("provedor", "demo")
    if provedor == "demo":
        return "<span class='pill-status'>● Modo demonstração</span>"
    if cfg.get("chave"):
        return f"<span class='pill-status ok'>● IA configurada · {escape(PROVEDORES[provedor].nome)}</span>"
    return "<span class='pill-status'>● IA não configurada</span>"


def cabecalho_pagina(eyebrow: str, titulo: str, subtitulo: str, status: bool = False) -> None:
    direita = _pill_ia() if status else ""
    html(f"""
    <div class='eyebrow'>{escape(eyebrow)}</div>
    <div class='pg-topo'><div class='pg-titulo'>{escape(titulo)}</div>{direita}</div>
    <p class='pg-sub'>{escape(subtitulo)}</p>""")


def regua() -> None:
    html("<hr class='regua'/>")


def secao(eyebrow: str, titulo: str, subtitulo: str = "") -> None:
    sub = f"<p class='sec-sub'>{escape(subtitulo)}</p>" if subtitulo else "<div style='height:1rem'></div>"
    html(f"<div class='eyebrow'>{escape(eyebrow)}</div><div class='sec-titulo'>{escape(titulo)}</div>{sub}")


def titulo_card(numero: str, titulo: str) -> None:
    numero_html = f"<span class='n'>{escape(numero)}</span>" if numero else ""
    html(f"<div class='card-titulo'>{numero_html}{escape(titulo)}</div>")


def metricas(itens: list[tuple[str, str]]) -> None:
    corpo = "".join(f"<div><div class='r'>{escape(r)}</div><div class='v'>{escape(v)}</div></div>" for r, v in itens)
    html(f"<div class='metricas'>{corpo}</div>")


def lista(itens: list[str], classe: str, simbolo: str, vazio: str) -> str:
    if not itens:
        return f"<p class='sutil'>{escape(vazio)}</p>"
    linhas = "".join(f"<li><span class='ico {classe}'>{simbolo}</span><span>{escape(i)}</span></li>" for i in itens)
    return f"<ul class='lista'>{linhas}</ul>"


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------
def _painel_resultado(analise: dict) -> None:
    transacao, motivo = analise.get("transacao", {}), analise.get("motivo", {})
    checklist = analise.get("checklist", {})
    meta = analise.get("meta", {})
    decisao = analise.get("decisao_analista") or "pendente"
    risco = analise.get("nivel_risco", "medio")

    with st.container(key=f"card_resultado_{analise.get('id', 0)}"):
        esq, dir_ = st.columns([1, 1.85], gap="large")
        with esq:
            html(f"""
            <div class='risco {risco}'>
              <div class='r'>Classificação de risco</div>
              <div class='v'>{escape(analise.get('nivel_risco_rotulo', ''))}</div>
              <div class='d'>Cobertura de evidências {checklist.get('cobertura', 0)}%</div>
            </div>""")
        with dir_:
            presentes = sum(1 for i in checklist.get("itens", []) if i["presente"])
            dados = [
                f"CASO {analise.get('numero', '')} · {moeda(transacao.get('valor'))}",
                f"Motivo: {motivo.get('rotulo', '')}"
                + (f" (código {motivo['codigo']})" if motivo.get("codigo") else ""),
            ]
            if motivo.get("prazo_resposta"):
                dados.append(f"Prazo de resposta: {motivo['prazo_resposta']}")
            dados.append(f"Motor: {meta.get('provedor_nome', '')} · {meta.get('gerado_em', '')}")
            html(f"""
            <div class='bloco-rot'>Resultado preliminar</div>
            <div>{pill(analise.get('status_rotulo', ''), CLASSE_STATUS.get(analise.get('status'), 'neutro'))}
                 {pill(banco.DECISOES.get(decisao, 'Pendente').split(' (')[0], CLASSE_DECISAO.get(decisao, 'neutro'))}</div>
            <div class='bloco-rot mt'>Dados principais</div>
            <ul class='marcadores'>{''.join(f'<li>{escape(d)}</li>' for d in dados)}</ul>
            <div class='bloco-rot mt'>Evidências por situação</div>
            <div>
              <span class='contagem'>{pill('Apresentadas', 'verde')}<b>{presentes}</b></span>
              <span class='contagem'>{pill('Obrigatórias ausentes', 'vermelho')}<b>{len(checklist.get('ausentes_obrigatorios', []))}</b></span>
              <span class='contagem'>{pill('Recomendadas ausentes', 'ambar')}<b>{len(checklist.get('ausentes_recomendados', []))}</b></span>
              <span class='contagem'>{pill('Inconsistências', 'azul')}<b>{len(analise.get('inconsistencias', []))}</b></span>
            </div>""")


def _aba_resumo(analise: dict) -> None:
    motivo = analise.get("motivo", {})
    with st.container(key=f"card_resumo_{analise.get('id', 0)}"):
        titulo_card("", "Resumo do caso")
        html(f"<p style='font-size:1.04rem'>{escape(analise.get('resumo', ''))}</p>"
             f"<div class='bloco-rot mt'>Motivo informado</div>"
             f"<p style='font-size:1.04rem'>{escape(motivo.get('descricao', ''))}</p>"
             f"<div class='recomendacao'><div class='t'>Recomendação da IA</div>"
             f"<div class='x'>{escape(analise.get('recomendacao', ''))}</div></div>")
        provs = "".join(f"<li><span class='ico info'>{i}</span><span>{escape(p)}</span></li>"
                        for i, p in enumerate(analise.get("providencias", []), start=1))
        html(f"<div class='bloco-rot'>Providências sugeridas</div><ul class='lista'>{provs}</ul>")


def _aba_evidencias(analise: dict) -> None:
    evid = analise.get("evidencias", [])
    with st.container(key=f"card_evid_{analise.get('id', 0)}"):
        titulo_card("", "Evidências identificadas")
        if evid:
            corpo = "".join(
                f"<li><span class='ico ok'>✓</span><span>{escape(e['descricao'])}<br/>"
                f"<span class='sutil'>{escape(e.get('arquivo', ''))}</span></span>"
                f"<span class='dir'>{pill(e['forca'].capitalize(), CLASSE_FORCA.get(e['forca'], 'neutro'))}</span></li>"
                for e in evid)
            html(f"<ul class='lista'>{corpo}</ul>")
        else:
            html("<p class='sutil'>Nenhuma evidência identificada.</p>")

    checklist = analise.get("checklist", {})
    st.write("")
    st.progress(checklist.get("cobertura", 0) / 100,
                text=f"Cobertura das evidências obrigatórias: {checklist.get('cobertura', 0)}%")
    st.dataframe(pd.DataFrame([{
        "Situação": "✅ Apresentado" if i["presente"] else ("❌ Ausente" if i["obrigatorio"] else "⚠️ Ausente"),
        "Documento": i["documento"],
        "Exigência": "Obrigatório" if i["obrigatorio"] else "Recomendado",
        "Por que é necessário": i["justificativa"],
    } for i in checklist.get("itens", [])]), hide_index=True, width="stretch")


def _aba_pontos(analise: dict) -> None:
    with st.container(key=f"card_pontos_{analise.get('id', 0)}"):
        titulo_card("", "Pontos de atenção")
        html(lista(analise.get("pontos_atencao", []), "alerta", "!", "Nenhum ponto de atenção."))
        html("<div class='bloco-rot mt'>Inconsistências entre documentos</div>")
        html(lista(analise.get("inconsistencias", []), "erro", "×",
                   "Nenhuma inconsistência identificada entre os documentos."))


def _aba_ausentes(analise: dict) -> None:
    ausentes = analise.get("documentos_ausentes", [])
    with st.container(key=f"card_ausentes_{analise.get('id', 0)}"):
        titulo_card("", "Documentos ausentes")
        if not ausentes:
            html("<p class='sutil'>Todos os documentos do checklist foram apresentados.</p>")
            return
        corpo = "".join(
            f"<li><span class='ico erro'>×</span><span><b>{escape(d['documento'])}</b><br/>"
            f"<span class='sutil'>{escape(d['justificativa'])}</span></span><span class='dir'>"
            f"{pill('Obrigatório', 'vermelho') if d['obrigatorio'] else pill('Recomendado', 'ambar')}</span></li>"
            for d in ausentes)
        html(f"<ul class='lista'>{corpo}</ul>")


def _aba_documentos(analise: dict) -> None:
    caso_id = analise.get("id")
    for i, d in enumerate(analise.get("documentos", [])):
        with st.expander(f"{d['arquivo']} — {rotulo_tipo(d['tipo'])}"):
            html(pill(rotulo_tipo(d["tipo"]), "azul") + pill(d.get("metodo", ""), "neutro")
                 + pill(f"{d.get('paginas', 0)} pág.", "neutro") + pill(f"{d.get('tamanho_kb', 0)} KB", "neutro"))
            st.markdown(f"**O que comprova:** {d.get('resumo', '')}")
            for aviso in d.get("avisos", []):
                st.caption(f"⚠️ {aviso}")
            dados = d.get("dados_extraidos") or {}
            if dados:
                st.dataframe(pd.DataFrame([{"Campo": rotulo_campo(k), "Valor": valor_campo(k, v)}
                                           for k, v in dados.items()]), hide_index=True, width="stretch")
            if caso_id:
                original = banco.obter_documento(caso_id, d["arquivo"])
                if original:
                    if original["mime"].startswith("image/"):
                        st.image(original["conteudo"], caption=d["arquivo"], width="stretch")
                    elif original.get("texto_extraido"):
                        st.text_area("Texto extraído", original["texto_extraido"], height=180,
                                     disabled=True, key=f"txt_{caso_id}_{i}")
                    st.download_button("Baixar original", original["conteudo"], file_name=d["arquivo"],
                                       mime=original["mime"], key=f"dl_{caso_id}_{i}")


def _aba_transacao(analise: dict) -> None:
    transacao = analise.get("transacao", {})
    if not transacao:
        st.info("Nenhum dado da transação foi identificado nos documentos.")
    else:
        st.dataframe(pd.DataFrame([{"Campo": rotulo_campo(k), "Valor": valor_campo(k, v)}
                                   for k, v in transacao.items()]), hide_index=True, width="stretch")
    if analise.get("observacoes"):
        st.caption(f"Contexto informado pelo analista: {analise['observacoes']}")


def formulario_parecer(analise: dict, prefixo: str = "rel", ao_abrir=None) -> None:
    """Formulário de decisão do analista. ``ao_abrir`` adiciona o botão "Abrir relatório completo"."""
    caso_id = analise.get("id")
    if not caso_id:
        return
    chaves = list(banco.DECISOES)
    atual = analise.get("decisao_analista") or "pendente"
    col1, col2 = st.columns([1, 2], gap="large")
    decisao = col1.selectbox("Decisão do analista", chaves, index=chaves.index(atual) if atual in chaves else 0,
                             format_func=banco.DECISOES.get, key=f"{prefixo}_dec_{caso_id}")
    notas = col2.text_area("Observações", value=analise.get("notas_analista") or "", height=100,
                           key=f"{prefixo}_notas_{caso_id}")
    b1, b2, _ = st.columns([1, 1.3, 3])
    if b1.button("Registrar decisão", key=f"{prefixo}_salvar_{caso_id}", type="primary", width="stretch"):
        banco.atualizar_decisao(caso_id, decisao, notas)
        st.toast("Decisão registrada.", icon="✅")
        st.rerun()
    if ao_abrir and b2.button("Abrir relatório completo", key=f"{prefixo}_abrir_{caso_id}", width="stretch"):
        ao_abrir(caso_id)


def exibir_relatorio(analise: dict) -> None:
    meta = analise.get("meta", {})
    if meta.get("fallback"):
        st.warning(f"A chamada ao LLM falhou e a análise foi feita em modo demonstração (regras). "
                   f"Motivo: {meta['fallback']}")

    _painel_resultado(analise)
    st.write("")

    caso = analise.get("id", 0)
    nome_base = f"dispute_ai_caso_{caso:03d}"
    c1, c2, _ = st.columns([1, 1, 2.6])
    c1.download_button("Baixar relatório PDF", gerar_pdf(analise), file_name=f"{nome_base}.pdf",
                       mime="application/pdf", width="stretch", key=f"pdf_{caso}")
    c2.download_button("Baixar dados JSON", json.dumps(analise, ensure_ascii=False, indent=2).encode("utf-8"),
                       file_name=f"{nome_base}.json", mime="application/json", width="stretch",
                       key=f"json_{caso}")
    st.write("")

    abas = st.tabs([
        "Resumo",
        f"Evidências ({len(analise.get('evidencias', []))})",
        f"Pontos de atenção ({len(analise.get('pontos_atencao', [])) + len(analise.get('inconsistencias', []))})",
        f"Documentos ausentes ({len(analise.get('documentos_ausentes', []))})",
        f"Documentos ({len(analise.get('documentos', []))})",
        "Dados da transação",
        "Parecer do analista",
    ])
    with abas[0]:
        _aba_resumo(analise)
    with abas[1]:
        _aba_evidencias(analise)
    with abas[2]:
        _aba_pontos(analise)
    with abas[3]:
        _aba_ausentes(analise)
    with abas[4]:
        _aba_documentos(analise)
    with abas[5]:
        _aba_transacao(analise)
    with abas[6]:
        with st.container(key=f"card_parecer_{caso}"):
            titulo_card("", "Parecer do analista")
            formulario_parecer(analise)

    html(f"<p class='aviso'>{escape(analise.get('aviso_legal', ''))}</p>")
