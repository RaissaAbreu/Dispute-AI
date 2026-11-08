"""Páginas da aplicação: Nova análise, Resultado, Revisão do analista, Histórico e Como funciona."""

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
from .componentes import (
    CLASSE_DECISAO,
    CLASSE_RISCO,
    CLASSE_STATUS,
    cabecalho_pagina,
    exibir_relatorio,
    formulario_parecer,
    html,
    metricas,
    pill,
    regua,
    secao,
    titulo_card,
)

PG_NOVA = "Nova análise"
PG_RESULTADO = "Resultado da análise"
PG_REVISAO = "Revisão do analista"
PG_HISTORICO = "Histórico"
PG_SOBRE = "Como funciona"
EYEBROW = "Operações de chargeback / Dispute AI"


def ir_para(pagina: str, caso_id: int | None = None) -> None:
    """Agenda a troca de página (aplicada antes de a navegação ser desenhada)."""
    st.session_state.destino = pagina
    if caso_id is not None:
        st.session_state.caso_atual = caso_id
    st.rerun()


def _rotulo_caso(c: dict) -> str:
    risco = (c.get("nivel_risco") or "").capitalize().replace("Medio", "Médio")
    return f"{banco.numero_caso(c['id'])} — {moeda(c['valor'])} · {rotulo_motivo(c['motivo'] or 'outro')} · {risco}"


# ---------------------------------------------------------------------------
# 01 · Nova análise
# ---------------------------------------------------------------------------
def _arquivos_exemplo() -> list[tuple[str, bytes]]:
    if not PASTA_EXEMPLOS.exists():
        return []
    return [(p.name, p.read_bytes()) for p in sorted(PASTA_EXEMPLOS.iterdir())
            if p.suffix.lstrip(".").lower() in TIPOS_ACEITOS]


def pagina_nova_analise() -> None:
    cabecalho_pagina(EYEBROW, "Análise de contestações",
                     "Extração de dados, organização de evidências e análise preliminar de chargebacks.",
                     status=True)
    regua()
    secao("Entrada do caso / 01", "Envio de documentos",
          "Envie os documentos do caso em PDF, TXT, e-mail (.eml) ou imagem para análise automática.")

    st.session_state.setdefault("versao_upload", 0)

    with st.container(key="card_upload"):
        titulo_card("01", "Documentos do caso")
        enviados = st.file_uploader(
            "Documentos do caso", type=list(TIPOS_ACEITOS), accept_multiple_files=True,
            label_visibility="collapsed", key=f"upload_{st.session_state.versao_upload}",
        )
        c1, c2, _ = st.columns([1.3, 0.8, 2])
        if c1.button("Usar caso demonstrativo", width="stretch",
                     help="Carrega documentos fictícios de uma venda de R$ 850,00 contestada."):
            st.session_state.usar_exemplos = True
            st.session_state.versao_upload += 1
            st.rerun()
        if c2.button("Limpar", width="stretch"):
            st.session_state.usar_exemplos = False
            st.session_state.versao_upload += 1
            st.rerun()

    arquivos: list[tuple[str, bytes]] = [(f.name, f.getvalue()) for f in (enviados or [])]
    if not arquivos and st.session_state.get("usar_exemplos"):
        arquivos = _arquivos_exemplo()

    st.write("")
    col_a, col_b = st.columns([1.15, 1], gap="large")
    with col_a:
        with st.container(key="card_arquivos"):
            titulo_card("02", f"Arquivos selecionados ({len(arquivos)})")
            if arquivos:
                itens = "".join(f"<li><span class='ico info'>{i}</span><span>{escape(n)}</span></li>"
                                for i, (n, _) in enumerate(arquivos, start=1))
                html(f"<ul class='lista'>{itens}</ul>")
                if st.session_state.get("usar_exemplos") and not enviados:
                    st.caption("Documentos fictícios do caso demonstrativo.")
            else:
                html("<p class='sutil'>Nenhum documento selecionado.</p>")
    with col_b:
        with st.container(key="card_contexto"):
            titulo_card("03", "Contexto adicional")
            observacoes = st.text_area(
                "Observações para a IA (opcional)", height=120,
                placeholder="Ex.: cliente recorrente; pedido retirado na loja física...",
            )
            cfg = st.session_state.config_llm
            motor = PROVEDORES[cfg["provedor"]].nome
            if cfg["provedor"] != "demo":
                motor += f" · {cfg['modelo']}"
            html(f"<p class='sutil'>Motor de análise: <b>{escape(motor)}</b></p>")

    st.write("")
    if not st.button("Analisar contestação", type="primary", disabled=not arquivos):
        return

    cfg = st.session_state.config_llm
    if cfg["provedor"] != "demo" and not cfg["chave"] and not cfg["fallback"]:
        st.error("Informe a chave de API na barra lateral ou selecione o modo demonstração.")
        return
    with st.status("Analisando o caso...", expanded=True) as status:
        st.write("Extraindo conteúdo dos documentos (PyMuPDF)...")
        docs = []
        for nome, dados in arquivos:
            try:
                docs.append(carregar_documento(nome, dados))
            except FormatoNaoSuportado as exc:
                st.write(f"⚠️ {nome}: {exc}")
        if not docs:
            status.update(label="Nenhum documento pôde ser lido.", state="error")
            return
        st.write(f"Analisando com {PROVEDORES[cfg['provedor']].nome}...")
        try:
            analise = analisar_caso(docs, cfg["provedor"], cfg["modelo"], cfg["chave"],
                                    observacoes, fallback_demo=cfg["fallback"])
        except ErroLLM as exc:
            status.update(label="Falha na análise.", state="error")
            st.error(str(exc))
            return
        st.write("Verificando checklist de evidências e salvando no histórico...")
        caso_id = banco.salvar_caso(analise, docs)
        status.update(label=f"Análise concluída — CASO {banco.numero_caso(caso_id)}", state="complete")
    ir_para(PG_RESULTADO, caso_id)


# ---------------------------------------------------------------------------
# 02 · Resultado da análise
# ---------------------------------------------------------------------------
def pagina_resultado() -> None:
    secao("Análise do caso / 02", "Resultado da análise",
          "Motivo identificado, evidências organizadas, documentos ausentes e classificação de risco.")

    casos = banco.listar_casos()
    if not casos:
        with st.container(key="card_vazio_res"):
            html("<div class='vazio'>Nenhum caso analisado ainda. Comece pela página <b>Nova análise</b>.</div>")
        return

    ids = [c["id"] for c in casos]
    atual = st.session_state.get("caso_atual")
    indice = ids.index(atual) if atual in ids else 0
    rotulos = {c["id"]: _rotulo_caso(c) for c in casos}
    with st.container(key="sel_caso"):
        caso_id = st.selectbox("Selecione um caso para consultar", ids, index=indice, format_func=rotulos.get)
    st.session_state.caso_atual = caso_id
    st.write("")

    analise = banco.obter_caso(caso_id)
    if analise:
        exibir_relatorio(analise)


# ---------------------------------------------------------------------------
# 03 · Revisão do analista
# ---------------------------------------------------------------------------
def pagina_revisao() -> None:
    cabecalho_pagina(EYEBROW, "Revisão do analista",
                     "Confira a análise automática e registre a decisão sobre cada contestação.")
    regua()
    secao("Controle / 03", "Central de revisão",
          "Casos aguardando decisão. A recomendação da IA é preliminar e precisa de validação humana.")

    por_decisao = banco.estatisticas()["por_decisao"]
    metricas([
        ("Aguardando decisão", str(por_decisao.get("pendente", 0))),
        ("Defender", str(por_decisao.get("defender", 0))),
        ("Aceitar chargeback", str(por_decisao.get("aceitar", 0))),
        ("Aguardando documentos", str(por_decisao.get("aguardando_docs", 0))),
    ])
    regua()

    todos = st.checkbox("Mostrar também casos já decididos")
    casos = [c for c in banco.listar_casos()
             if todos or c["decisao_analista"] in ("pendente", "aguardando_docs")]
    if not casos:
        with st.container(key="card_vazio_rev"):
            html("<div class='vazio'>Nenhum caso aguardando revisão.</div>")
        return

    for c in casos:
        analise = banco.obter_caso(c["id"])
        if not analise:
            continue
        with st.container(key=f"card_rev_{c['id']}"):
            decisao = c["decisao_analista"] or "pendente"
            html(f"""
            <div class='pg-topo'>
              <div class='card-titulo'><span class='n'>{escape(banco.numero_caso(c['id']))}</span>
                {escape(moeda(c['valor']))} · {escape(rotulo_motivo(c['motivo'] or 'outro'))}</div>
              <div>{pill(STATUS.get(c['status'], ''), CLASSE_STATUS.get(c['status'], 'neutro'))}
                   {pill('Risco ' + analise.get('nivel_risco_rotulo', '').lower(), CLASSE_RISCO.get(analise.get('nivel_risco'), 'neutro'))}
                   {pill(banco.DECISOES.get(decisao, '').split(' (')[0], CLASSE_DECISAO.get(decisao, 'neutro'))}</div>
            </div>
            <p class='sutil'>Analisado em {escape(data_hora(c['criado_em']))} · {c['qtd_documentos']} documento(s)</p>
            <div class='recomendacao'><div class='t'>Recomendação da IA</div>
              <div class='x'>{escape(analise.get('recomendacao', ''))}</div></div>""")
            formulario_parecer(analise, prefixo="rev", ao_abrir=lambda cid: ir_para(PG_RESULTADO, cid))
        st.write("")


# ---------------------------------------------------------------------------
# 04 · Histórico
# ---------------------------------------------------------------------------
def pagina_historico() -> None:
    cabecalho_pagina(EYEBROW, "Histórico de casos", "Consulte, filtre e reabra as análises salvas no banco de dados.")
    regua()
    secao("Arquivo / 04", "Casos analisados")

    stats = banco.estatisticas()
    metricas([
        ("Casos analisados", str(stats["total"])),
        ("Valor contestado", moeda(stats["valor_total"])),
        ("Revisão necessária", str(stats["por_status"].get("revisao", 0))),
        ("Aguardando decisão", str(stats["pendentes"])),
    ])
    regua()

    casos = banco.listar_casos()
    if not casos:
        with st.container(key="card_vazio_hist"):
            html("<div class='vazio'>Nenhum caso analisado ainda.</div>")
        return

    c1, c2, c3 = st.columns([2, 2, 3])
    f_status = c1.multiselect("Status", list(STATUS), format_func=STATUS.get, placeholder="Todos")
    f_motivo = c2.multiselect("Motivo", list(MOTIVOS), format_func=MOTIVOS.get, placeholder="Todos")
    busca = c3.text_input("Buscar", placeholder="Número do caso ou trecho do resumo")

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
        "Decisão": banco.DECISOES.get(c["decisao_analista"], "").split(" (")[0],
        "Motor": c["modelo"],
    } for c in filtrados])

    st.caption(f"{len(filtrados)} caso(s). Selecione uma linha para abrir ou excluir.")
    selecao = st.dataframe(tabela, hide_index=True, width="stretch",
                           on_select="rerun", selection_mode="single-row", key="tabela_casos")
    linhas = selecao.selection.rows if selecao else []
    if not linhas:
        return

    caso = filtrados[linhas[0]]
    numero = banco.numero_caso(caso["id"])
    a, b, _ = st.columns([1.2, 1.2, 2])
    if a.button(f"Abrir resultado do caso {numero}", type="primary", width="stretch"):
        ir_para(PG_RESULTADO, caso["id"])
    with b.popover("Excluir caso", width="stretch"):
        st.write(f"Remover definitivamente o CASO {numero} e seus documentos?")
        if st.button("Confirmar exclusão", key=f"exc_{caso['id']}"):
            banco.excluir_caso(caso["id"])
            if st.session_state.get("caso_atual") == caso["id"]:
                st.session_state.pop("caso_atual")
            st.toast("Caso excluído.")
            st.rerun()


# ---------------------------------------------------------------------------
# 05 · Como funciona
# ---------------------------------------------------------------------------
def pagina_como_funciona() -> None:
    cabecalho_pagina(EYEBROW, "Como funciona", "Fluxo de análise, critérios utilizados e limites da ferramenta.")
    regua()
    secao("Referência / 05", "Fluxo de análise")
    etapas = [
        ("Upload", "PDF, TXT, e-mails (.eml) e imagens dos documentos do caso."),
        ("Extração", "PyMuPDF lê o texto dos PDFs; páginas digitalizadas e imagens vão para o LLM com visão."),
        ("Motivo", "A IA classifica o motivo da contestação (ex.: compra não reconhecida)."),
        ("Evidências", "Cada documento é classificado e as evidências são organizadas por força."),
        ("Ausências", "Um checklist determinístico por motivo aponta documentos obrigatórios ausentes."),
        ("Relatório", "Status, risco, recomendação e providências, em tela e em PDF."),
    ]
    for inicio in (0, 3):
        cols = st.columns(3, gap="medium")
        for col, (i, (t, d)) in zip(cols, enumerate(etapas[inicio:inicio + 3], start=inicio + 1)):
            with col, st.container(key=f"card_etapa_{i}"):
                titulo_card(f"{i:02d}", t)
                html(f"<p class='sutil' style='font-size:.98rem'>{escape(d)}</p>")
        st.write("")

    regua()
    secao("Referência / 06", "Checklist de evidências por motivo")
    linhas = "".join(
        f"<tr><td><b>{escape(rotulo_motivo(m))}</b></td>"
        f"<td>{''.join(pill(rotulo_tipo(t), 'vermelho') for t in r['obrigatorios'])}</td>"
        f"<td>{''.join(pill(rotulo_tipo(t), 'ambar') for t in r['recomendados'])}</td></tr>"
        for m, r in CHECKLIST.items())
    with st.container(key="card_checklist"):
        html(f"<table class='tabela'><tr><th>Motivo</th><th>Obrigatórios</th><th>Recomendados</th></tr>"
             f"{linhas}</table>")

    st.write("")
    st.markdown(
        "**Motores de análise.** Com Anthropic, OpenAI ou Gemini, a leitura é completa (inclusive imagens) "
        "e a análise é contextual. O modo demonstração usa regras, sem custo e sem envio de dados, mas não "
        "lê imagens. Em todos os modos, o status nunca é *Evidências suficientes* quando falta um documento "
        "obrigatório, e a decisão final é sempre do analista."
    )
    st.info("Use apenas documentos fictícios ou anonimizados. Ao usar um provedor de LLM, o conteúdo dos "
            "documentos é enviado à API do provedor selecionado.")
