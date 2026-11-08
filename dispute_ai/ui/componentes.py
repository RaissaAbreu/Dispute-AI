"""Componentes visuais reutilizáveis: exibição do relatório de análise de um caso."""

from __future__ import annotations

import json
from html import escape

import pandas as pd
import streamlit as st

from .. import banco
from ..catalogo import rotulo_tipo
from ..formatacao import moeda, rotulo_campo, valor_campo
from ..relatorio import gerar_pdf


def html(conteudo: str) -> None:
    """Renderiza HTML (remove indentação para não virar bloco de código no Markdown)."""
    st.markdown("".join(linha.strip() for linha in conteudo.splitlines()), unsafe_allow_html=True)


def hero(titulo: str, subtitulo: str) -> None:
    html(f"<div class='da-hero'><h1>{escape(titulo)}</h1><p>{escape(subtitulo)}</p></div>")


def lista_icones(itens: list[str], classe: str, simbolo: str, vazio: str) -> str:
    if not itens:
        return f"<p class='da-sub'>{escape(vazio)}</p>"
    linhas = "".join(
        f"<li><span class='da-ico {classe}'>{simbolo}</span><span>{escape(i)}</span></li>" for i in itens
    )
    return f"<ul class='da-lista'>{linhas}</ul>"


def card(titulo: str, corpo: str) -> None:
    html(f"<div class='da-card'><h4>{escape(titulo)}</h4>{corpo}</div>")


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------
def _cabecalho(analise: dict) -> None:
    meta = analise.get("meta", {})
    origem = f"{meta.get('provedor_nome', '')} · {meta.get('modelo', '')} · {meta.get('gerado_em', '')}"
    html(f"""
    <div class='da-card'>
      <div class='da-caso-topo'>
        <div>
          <div class='da-rotulo'>Análise de contestação</div>
          <div class='da-caso-num'>CASO {escape(analise.get('numero', ''))}</div>
          <div class='da-sub'>{escape(origem)}</div>
        </div>
        <span class='da-badge {analise['status']}'>{escape(analise['status_rotulo'])}</span>
      </div>
    </div>""")

    transacao, motivo = analise.get("transacao", {}), analise.get("motivo", {})
    cobertura = analise.get("checklist", {}).get("cobertura", 0)
    html(f"""
    <div class='da-kpis'>
      <div class='da-kpi'><div class='da-rotulo'>Valor contestado</div>
        <div class='v'>{escape(moeda(transacao.get('valor')))}</div></div>
      <div class='da-kpi'><div class='da-rotulo'>Motivo</div>
        <div class='v' style='font-size:1rem'>{escape(motivo.get('rotulo', ''))}</div></div>
      <div class='da-kpi'><div class='da-rotulo'>Risco de perda</div>
        <div class='v {analise['nivel_risco']}'>{escape(analise['nivel_risco_rotulo'])}</div></div>
      <div class='da-kpi'><div class='da-rotulo'>Cobertura de evidências</div>
        <div class='v'>{cobertura}%</div></div>
    </div>""")


def _aba_analise(analise: dict) -> None:
    motivo = analise.get("motivo", {})
    col1, col2 = st.columns([3, 2], gap="medium")
    with col1:
        card("Resumo", f"<p>{escape(analise.get('resumo', ''))}</p>")
        extras = []
        if motivo.get("codigo"):
            extras.append(f"<span class='da-chip'>Código {escape(str(motivo['codigo']))}</span>")
        if motivo.get("prazo_resposta"):
            extras.append(f"<span class='da-chip'>Prazo: {escape(str(motivo['prazo_resposta']))}</span>")
        card("Motivo informado",
             f"<p><b>{escape(motivo.get('descricao', ''))}</b></p>{''.join(extras)}")
        evid = analise.get("evidencias", [])
        corpo = "".join(
            f"<li><span class='da-ico ok'>✓</span><span>{escape(e['descricao'])}"
            f"<br/><span class='da-sub'>{escape(e.get('arquivo', ''))}</span></span>"
            f"<span style='margin-left:auto'><span class='da-chip {e['forca']}'>{escape(e['forca'])}</span></span></li>"
            for e in evid
        )
        card("Evidências identificadas",
             f"<ul class='da-lista'>{corpo}</ul>" if evid else "<p class='da-sub'>Nenhuma evidência identificada.</p>")
    with col2:
        card("Pontos de atenção", lista_icones(analise.get("pontos_atencao", []), "alerta", "!",
                                               "Nenhum ponto de atenção."))
        card("Inconsistências", lista_icones(analise.get("inconsistencias", []), "erro", "×",
                                             "Nenhuma inconsistência identificada entre os documentos."))

    html(f"<div class='da-rec'><div class='t'>Recomendação da IA</div>"
         f"<div class='r'>{escape(analise.get('recomendacao', ''))}</div></div>")
    provs = "".join(
        f"<li><span class='da-ico info'>{i}</span><span>{escape(p)}</span></li>"
        for i, p in enumerate(analise.get("providencias", []), start=1)
    )
    card("Providências sugeridas", f"<ul class='da-lista'>{provs}</ul>")


def _aba_checklist(analise: dict) -> None:
    checklist = analise.get("checklist", {})
    st.progress(checklist.get("cobertura", 0) / 100,
                text=f"Cobertura das evidências obrigatórias: {checklist.get('cobertura', 0)}%")
    linhas = [{
        "Situação": "✅ Apresentado" if i["presente"] else ("❌ Ausente" if i["obrigatorio"] else "⚠️ Ausente"),
        "Documento": i["documento"],
        "Exigência": "Obrigatório" if i["obrigatorio"] else "Recomendado",
        "Por que é necessário": i["justificativa"],
    } for i in checklist.get("itens", [])]
    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")

    ausentes = analise.get("documentos_ausentes", [])
    itens = [f"{d['documento']} ({'obrigatório' if d['obrigatorio'] else 'recomendado'}) — {d['justificativa']}"
             for d in ausentes]
    card("Documentos ausentes", lista_icones(itens, "erro", "×",
                                             "Todos os documentos do checklist foram apresentados."))


def _aba_documentos(analise: dict) -> None:
    caso_id = analise.get("id")
    for i, d in enumerate(analise.get("documentos", [])):
        with st.expander(f"📄 {d['arquivo']} — {rotulo_tipo(d['tipo'])}", expanded=False):
            html(f"<span class='da-chip'>{escape(rotulo_tipo(d['tipo']))}</span>"
                 f"<span class='da-chip'>{escape(d.get('metodo', ''))}</span>"
                 f"<span class='da-chip'>{d.get('paginas', 0)} pág.</span>"
                 f"<span class='da-chip'>{d.get('tamanho_kb', 0)} KB</span>")
            st.markdown(f"**O que comprova:** {d.get('resumo', '')}")
            for aviso in d.get("avisos", []):
                st.caption(f"⚠️ {aviso}")
            dados = d.get("dados_extraidos") or {}
            if dados:
                st.dataframe(
                    pd.DataFrame([{"Campo": rotulo_campo(k), "Valor": valor_campo(k, v)} for k, v in dados.items()]),
                    hide_index=True, width="stretch",
                )
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
        st.dataframe(
            pd.DataFrame([{"Campo": rotulo_campo(k), "Valor": valor_campo(k, v)} for k, v in transacao.items()]),
            hide_index=True, width="stretch",
        )
    if analise.get("observacoes"):
        card("Contexto informado pelo analista", f"<p>{escape(analise['observacoes'])}</p>")


def _parecer(analise: dict) -> None:
    caso_id = analise.get("id")
    if not caso_id:
        return
    with st.container(border=True):
        st.markdown("##### 🧑‍💼 Parecer do analista")
        chaves = list(banco.DECISOES)
        atual = analise.get("decisao_analista") or "pendente"
        col1, col2 = st.columns([1, 2])
        decisao = col1.selectbox("Decisão", chaves, index=chaves.index(atual) if atual in chaves else 0,
                                 format_func=banco.DECISOES.get, key=f"dec_{caso_id}")
        notas = col2.text_area("Observações", value=analise.get("notas_analista") or "", height=90,
                               key=f"notas_{caso_id}")
        if st.button("Salvar parecer", key=f"salvar_{caso_id}"):
            banco.atualizar_decisao(caso_id, decisao, notas)
            st.toast("Parecer salvo.", icon="✅")
            st.rerun()


def exibir_relatorio(analise: dict) -> None:
    meta = analise.get("meta", {})
    if meta.get("fallback"):
        st.warning(f"A chamada ao LLM falhou e a análise foi feita em modo demonstração (regras). "
                   f"Motivo: {meta['fallback']}")

    _cabecalho(analise)

    col_a, col_b, _ = st.columns([1.2, 1, 3])
    nome_base = f"dispute_ai_caso_{analise.get('id', 0):03d}"
    col_a.download_button("⬇ Relatório PDF", gerar_pdf(analise), file_name=f"{nome_base}.pdf",
                          mime="application/pdf", type="primary", width="stretch",
                          key=f"pdf_{analise.get('id')}")
    col_b.download_button("⬇ JSON", json.dumps(analise, ensure_ascii=False, indent=2).encode("utf-8"),
                          file_name=f"{nome_base}.json", mime="application/json",
                          width="stretch", key=f"json_{analise.get('id')}")

    abas = st.tabs(["Análise", "Evidências e checklist", "Documentos", "Dados da transação"])
    with abas[0]:
        _aba_analise(analise)
    with abas[1]:
        _aba_checklist(analise)
    with abas[2]:
        _aba_documentos(analise)
    with abas[3]:
        _aba_transacao(analise)

    _parecer(analise)
    html(f"<p class='da-aviso'>{escape(analise.get('aviso_legal', ''))}</p>")
