"""Dispute AI — Assistente inteligente para análise de contestações e chargebacks.

Execute com:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from dispute_ai import __version__, banco
from dispute_ai.config import PROVEDOR_PADRAO, PROVEDORES, chave_api_ambiente
from dispute_ai.ui.estilos import aplicar_estilos
from dispute_ai.ui.paginas import (
    PG_HISTORICO,
    PG_NOVA,
    PG_RESULTADO,
    PG_REVISAO,
    PG_SOBRE,
    pagina_como_funciona,
    pagina_historico,
    pagina_nova_analise,
    pagina_resultado,
    pagina_revisao,
)

st.set_page_config(page_title="Dispute AI", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
aplicar_estilos()
banco.inicializar()

PAGINAS = {
    PG_NOVA: pagina_nova_analise,
    PG_RESULTADO: pagina_resultado,
    PG_REVISAO: pagina_revisao,
    PG_HISTORICO: pagina_historico,
    PG_SOBRE: pagina_como_funciona,
}
OPCAO_PERSONALIZADO = "Outro (digitar)…"


def secao_sidebar(texto: str) -> None:
    st.markdown(f"<div class='sb-secao'>{texto}</div>", unsafe_allow_html=True)


def barra_lateral() -> str:
    # Troca de página solicitada por outra tela (ex.: após concluir uma análise).
    if "destino" in st.session_state:
        st.session_state.pagina = st.session_state.pop("destino")

    with st.sidebar:
        st.markdown("<div class='sb-marca'><div class='t'>Dispute AI</div>"
                    "<div class='s'>Inteligência em contestações</div></div>", unsafe_allow_html=True)
        st.divider()

        secao_sidebar("Área de trabalho")
        pagina = st.radio("Navegação", list(PAGINAS), key="pagina", label_visibility="collapsed")
        st.divider()

        secao_sidebar("Inteligência artificial")
        chaves = list(PROVEDORES)
        provedor = st.selectbox("Provedor", chaves, index=chaves.index(PROVEDOR_PADRAO),
                                format_func=lambda k: PROVEDORES[k].nome)
        p = PROVEDORES[provedor]
        chave, fallback, modelo = "", True, p.modelo_padrao

        if provedor != "demo":
            escolhido = st.selectbox("Modelo", p.modelos + [OPCAO_PERSONALIZADO], key=f"modelo_{provedor}")
            modelo = (st.text_input("Nome do modelo", key=f"modelo_custom_{provedor}").strip()
                      if escolhido == OPCAO_PERSONALIZADO else escolhido)
            chave_env = chave_api_ambiente(provedor)
            chave_digitada = st.text_input(
                "Chave de API", type="password", key=f"chave_{provedor}",
                placeholder="Usando a chave do .env" if chave_env else "Cole sua chave aqui",
                help=f"Também pode ser definida na variável {p.variavel_ambiente} do arquivo .env. "
                     "A chave digitada fica apenas nesta sessão.",
            )
            chave = chave_digitada.strip() or chave_env
            estado = "● Chave configurada" if chave else f"● {p.variavel_ambiente} ausente no .env"
            st.markdown(f"<div class='sb-status'>{estado}</div>", unsafe_allow_html=True)
            fallback = st.toggle("Usar modo demonstração se a API falhar", value=True)
        else:
            st.markdown("<div class='sb-status'>● Análise por regras, sem envio de dados</div>",
                        unsafe_allow_html=True)

        st.session_state.config_llm = {"provedor": provedor, "modelo": modelo or p.modelo_padrao,
                                       "chave": chave, "fallback": fallback}
        st.divider()
        secao_sidebar("Operações de chargeback")
        st.markdown("<div class='sb-rodape'>Análise inteligente de contestações.</div>", unsafe_allow_html=True)
        st.caption(f"Versão {__version__} · Use somente documentos fictícios ou anonimizados.")
    return pagina


PAGINAS[barra_lateral()]()
