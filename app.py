"""Dispute AI — Assistente inteligente para análise de contestações e chargebacks.

Execute com:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from dispute_ai import __version__, banco
from dispute_ai.config import PROVEDOR_PADRAO, PROVEDORES, chave_api_ambiente
from dispute_ai.ui.estilos import aplicar_estilos
from dispute_ai.ui.paginas import pagina_como_funciona, pagina_historico, pagina_nova_analise

st.set_page_config(page_title="Dispute AI", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")
aplicar_estilos()
banco.inicializar()

OPCAO_PERSONALIZADO = "Outro (digitar)…"


def barra_lateral() -> None:
    with st.sidebar:
        st.markdown(
            "<div class='da-marca'><div class='da-logo'>DA</div><div>"
            "<div class='da-nome'>Dispute AI</div>"
            "<div class='da-slogan'>Análise de contestações e chargebacks</div></div></div>",
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown("**⚙️ Motor de análise**")

        chaves = list(PROVEDORES)
        provedor = st.selectbox(
            "Provedor", chaves, index=chaves.index(PROVEDOR_PADRAO),
            format_func=lambda k: PROVEDORES[k].nome,
        )
        p = PROVEDORES[provedor]
        chave, fallback, modelo = "", True, p.modelo_padrao

        if provedor != "demo":
            opcoes = p.modelos + [OPCAO_PERSONALIZADO]
            escolhido = st.selectbox("Modelo", opcoes, key=f"modelo_{provedor}")
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
            if chave:
                st.caption("🟢 Chave configurada")
            else:
                st.caption("🔴 Nenhuma chave configurada")
            fallback = st.toggle("Usar modo demonstração se a API falhar", value=True)
        else:
            st.caption("Análise por regras, sem custo e sem envio de dados a terceiros. "
                       "Imagens não são lidas neste modo.")

        st.session_state.config_llm = {"provedor": provedor, "modelo": modelo or p.modelo_padrao,
                                       "chave": chave, "fallback": fallback}
        st.divider()
        st.caption(f"Versão {__version__} · Use somente documentos fictícios ou anonimizados.")


barra_lateral()

navegacao = st.navigation([
    st.Page(pagina_nova_analise, title="Nova análise", icon="🔎", url_path="nova-analise", default=True),
    st.Page(pagina_historico, title="Histórico de casos", icon="🗂️", url_path="historico"),
    st.Page(pagina_como_funciona, title="Como funciona", icon="ℹ️", url_path="como-funciona"),
])
navegacao.run()
