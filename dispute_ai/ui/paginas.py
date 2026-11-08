"""Páginas da aplicação: Nova análise, Histórico de casos e Como funciona."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from .. import banco
from ..analisador import analisar_caso
from ..catalogo import CHECKLIST, MOTIVOS, STATUS, rotulo_motivo, rotulo_tipo
from ..config import PASTA_EXEMPLOS, PROVEDORES, TIPOS_ACEITOS
from ..extracao import FormatoNaoSuportado, carregar_documento
from ..formatacao import data_hora, moeda
from ..llm import ErroLLM
from .componentes import exibir_relatorio, hero, html


# ---------------------------------------------------------------------------
# Nova análise
# ---------------------------------------------------------------------------
def _arquivos_exemplo() -> list[tuple[str, bytes]]:
    if not PASTA_EXEMPLOS.exists():
        return []
    return [(p.name, p.read_bytes()) for p in sorted(PASTA_EXEMPLOS.iterdir())
            if p.suffix.lstrip(".").lower() in TIPOS_ACEITOS]


def pagina_nova_analise() -> None:
    hero("Nova análise de contestação",
         "Envie os documentos do caso. A IA extrai os dados, identifica o motivo, organiza as "
         "evidências, aponta documentos ausentes e gera um relatório preliminar.")

    if "versao_upload" not in st.session_state:
        st.session_state.versao_upload = 0

    col_up, col_info = st.columns([3, 2], gap="large")
    with col_up:
        enviados = st.file_uploader(
            "Documentos do caso",
            type=list(TIPOS_ACEITOS),
            accept_multiple_files=True,
            help="PDF, TXT, E-mail (.eml) e imagens (PNG, JPG, WEBP). Até 25 MB por arquivo.",
            key=f"upload_{st.session_state.versao_upload}",
        )
        c1, c2 = st.columns(2)
        if c1.button("📂 Usar caso demonstrativo", width="stretch",
                     help="Carrega documentos fictícios de uma venda de R$ 850,00 contestada."):
            st.session_state.usar_exemplos = True
            st.session_state.versao_upload += 1
            st.rerun()
        if c2.button("Limpar", width="stretch"):
            st.session_state.usar_exemplos = False
            st.session_state.pop("caso_atual", None)
            st.session_state.versao_upload += 1
            st.rerun()

        with st.expander("Contexto adicional (opcional)"):
            observacoes = st.text_area(
                "Observações para a IA", height=90,
                placeholder="Ex.: cliente recorrente; pedido retirado na loja física...",
                label_visibility="collapsed",
            )

    arquivos: list[tuple[str, bytes]] = [(f.name, f.getvalue()) for f in (enviados or [])]
    if not arquivos and st.session_state.get("usar_exemplos"):
        arquivos = _arquivos_exemplo()

    with col_info:
        cfg = st.session_state.config_llm
        modo = PROVEDORES[cfg["provedor"]].nome
        itens = "".join(f"<li><span class='da-ico info'>{i}</span><span>{escape(n)}</span></li>"
                        for i, (n, _) in enumerate(arquivos, start=1))
        corpo = (f"<ul class='da-lista'>{itens}</ul>" if arquivos
                 else "<p class='da-sub'>Nenhum documento selecionado.</p>")
        html(f"<div class='da-card'><h4>Documentos do caso ({len(arquivos)})</h4>{corpo}"
             f"<p class='da-sub' style='margin-top:.6rem'>Motor de análise: <b>{escape(modo)}</b>"
             f"{' · ' + escape(cfg['modelo']) if cfg['provedor'] != 'demo' else ''}</p></div>")
        if st.session_state.get("usar_exemplos") and not enviados:
            st.caption("📌 Usando os documentos fictícios do caso demonstrativo.")

    analisar = st.button("🔎 Analisar contestação", type="primary", disabled=not arquivos)

    if analisar:
        cfg = st.session_state.config_llm
        if cfg["provedor"] != "demo" and not cfg["chave"] and not cfg["fallback"]:
            st.error("Informe a chave de API na barra lateral ou selecione o modo demonstração.")
            return
        with st.status("Analisando o caso...", expanded=True) as status:
            st.write("📄 Extraindo conteúdo dos documentos (PyMuPDF)...")
            docs, erros = [], []
            for nome, dados in arquivos:
                try:
                    docs.append(carregar_documento(nome, dados))
                except FormatoNaoSuportado as exc:
                    erros.append(f"{nome}: {exc}")
            for e in erros:
                st.write(f"⚠️ {e}")
            if not docs:
                status.update(label="Nenhum documento pôde ser lido.", state="error")
                return

            st.write(f"🤖 Analisando com {PROVEDORES[cfg['provedor']].nome}...")
            try:
                analise = analisar_caso(docs, cfg["provedor"], cfg["modelo"], cfg["chave"],
                                        observacoes, fallback_demo=cfg["fallback"])
            except ErroLLM as exc:
                status.update(label="Falha na análise.", state="error")
                st.error(str(exc))
                return

            st.write("✅ Verificando checklist de evidências e documentos ausentes...")
            st.write("💾 Salvando caso no histórico (SQLite)...")
            caso_id = banco.salvar_caso(analise, docs)
            status.update(label=f"Análise concluída — CASO {banco.numero_caso(caso_id)}",
                          state="complete", expanded=False)
        st.session_state.caso_atual = caso_id

    caso_id = st.session_state.get("caso_atual")
    if caso_id:
        analise = banco.obter_caso(caso_id)
        if analise:
            st.divider()
            exibir_relatorio(analise)


# ---------------------------------------------------------------------------
# Histórico
# ---------------------------------------------------------------------------
def pagina_historico() -> None:
    hero("Histórico de casos", "Consulte, filtre e reabra as análises salvas no banco de dados.")

    stats = banco.estatisticas()
    html(f"""
    <div class='da-kpis'>
      <div class='da-kpi'><div class='da-rotulo'>Casos analisados</div><div class='v'>{stats['total']}</div></div>
      <div class='da-kpi'><div class='da-rotulo'>Valor total contestado</div>
        <div class='v'>{escape(moeda(stats['valor_total']))}</div></div>
      <div class='da-kpi'><div class='da-rotulo'>Revisão necessária</div>
        <div class='v medio'>{stats['por_status'].get('revisao', 0)}</div></div>
      <div class='da-kpi'><div class='da-rotulo'>Aguardando decisão</div>
        <div class='v'>{stats['pendentes']}</div></div>
    </div>""")

    casos = banco.listar_casos()
    if not casos:
        st.info("Nenhum caso analisado ainda. Comece pela página **Nova análise**.")
        return

    c1, c2, c3 = st.columns([2, 2, 3])
    f_status = c1.multiselect("Status", list(STATUS), format_func=STATUS.get, placeholder="Todos")
    f_motivo = c2.multiselect("Motivo", list(MOTIVOS), format_func=MOTIVOS.get, placeholder="Todos")
    busca = c3.text_input("Buscar no resumo", placeholder="Ex.: 850, entrega...")

    filtrados = [c for c in casos
                 if (not f_status or c["status"] in f_status)
                 and (not f_motivo or c["motivo"] in f_motivo)
                 and (not busca or busca.lower() in (c["resumo"] or "").lower()
                      or busca in banco.numero_caso(c["id"]))]

    tabela = pd.DataFrame([{
        "Caso": banco.numero_caso(c["id"]),
        "Data": data_hora(c["criado_em"]),
        "Valor": moeda(c["valor"]),
        "Motivo": rotulo_motivo(c["motivo"] or "outro"),
        "Status": STATUS.get(c["status"], c["status"]),
        "Risco": (c["nivel_risco"] or "").capitalize().replace("Medio", "Médio"),
        "Docs": c["qtd_documentos"],
        "Decisão": banco.DECISOES.get(c["decisao_analista"], ""),
        "Motor": c["modelo"],
    } for c in filtrados])

    st.caption(f"{len(filtrados)} caso(s). Selecione uma linha para abrir o relatório.")
    selecao = st.dataframe(tabela, hide_index=True, width="stretch",
                           on_select="rerun", selection_mode="single-row", key="tabela_casos")

    linhas = selecao.selection.rows if selecao else []
    if not linhas:
        return
    caso_id = filtrados[linhas[0]]["id"]
    analise = banco.obter_caso(caso_id)
    if not analise:
        return
    st.divider()
    exibir_relatorio(analise)

    with st.expander("🗑️ Excluir caso"):
        st.write(f"Esta ação remove definitivamente o CASO {analise['numero']} e seus documentos.")
        if st.checkbox("Confirmo a exclusão", key=f"conf_exc_{caso_id}"):
            if st.button("Excluir definitivamente", key=f"exc_{caso_id}"):
                banco.excluir_caso(caso_id)
                if st.session_state.get("caso_atual") == caso_id:
                    st.session_state.pop("caso_atual")
                st.toast("Caso excluído.")
                st.rerun()


# ---------------------------------------------------------------------------
# Como funciona
# ---------------------------------------------------------------------------
def pagina_como_funciona() -> None:
    hero("Como funciona", "Fluxo de análise, critérios utilizados e limites da ferramenta.")
    etapas = [
        ("Upload", "PDF, TXT, e-mails (.eml) e imagens dos documentos do caso."),
        ("Extração", "PyMuPDF lê o texto dos PDFs; páginas digitalizadas e imagens vão para o LLM com visão."),
        ("Motivo", "A IA classifica o motivo da contestação (ex.: compra não reconhecida)."),
        ("Evidências", "Cada documento é classificado e as evidências são organizadas por força."),
        ("Ausências", "Um checklist determinístico por motivo aponta documentos obrigatórios ausentes."),
        ("Relatório", "Análise preliminar com status, risco, recomendação e providências, em tela e PDF."),
    ]
    cols = st.columns(3)
    for i, (t, d) in enumerate(etapas):
        with cols[i % 3]:
            html(f"<div class='da-card'><h4><span class='da-ico info'>{i + 1}</span> {escape(t)}</h4>"
                 f"<p class='da-sub'>{escape(d)}</p></div>")

    st.markdown("#### Checklist de evidências por motivo")
    linhas = []
    for motivo, regra in CHECKLIST.items():
        linhas.append({
            "Motivo": rotulo_motivo(motivo),
            "Obrigatórios": ", ".join(rotulo_tipo(t) for t in regra["obrigatorios"]),
            "Recomendados": ", ".join(rotulo_tipo(t) for t in regra["recomendados"]),
        })
    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch")

    st.markdown("#### Motores de análise")
    st.markdown(
        "- **Anthropic, OpenAI ou Gemini**: leitura completa (inclusive imagens) e análise contextual.\n"
        "- **Modo demonstração**: regras e expressões regulares, sem custo e sem envio de dados; "
        "não lê imagens.\n\n"
        "Em todos os modos, o status nunca é *Evidências suficientes* quando falta um documento "
        "obrigatório, e a recomendação final é sempre submetida a um analista humano."
    )
    st.info("⚠️ Use apenas documentos fictícios ou anonimizados. Ao usar um provedor de LLM, o "
            "conteúdo dos documentos é enviado à API do provedor selecionado.")
