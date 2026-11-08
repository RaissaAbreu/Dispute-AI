"""Identidade visual executiva: fundo creme, tipografia serifada, acentos dourados e azul-marinho."""

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Source+Sans+3:wght@400;600;700;800&display=swap');

:root {
  --creme: #F5F3EE; --creme-2: #FBF9F4; --navy: #13213F; --navy-2: #1E2E52;
  --ouro: #A87C2A; --ouro-claro: #C9A45C; --tinta: #1C1F26; --texto: #2E3440;
  --sutil: #5F6673; --borda: #E4DED2; --regua: #D9D3C7;
  --verde: #2F6B4F; --ambar: #8A5F10; --vermelho: #9A3B22;
  --serif: 'Cormorant Garamond', Georgia, 'Times New Roman', serif;
  --sans: 'Source Sans 3', 'Source Sans Pro', -apple-system, 'Segoe UI', sans-serif;
}

html, body, .stApp, [data-testid="stAppViewContainer"] { background: var(--creme); font-family: var(--sans); }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { max-width: 1240px; padding: 3.2rem 3.5rem 4rem 3.5rem; }
p, li, label, span, div { font-family: var(--sans); }

/* ---------------- Barra lateral ---------------- */
section[data-testid="stSidebar"] { background: var(--navy); }
section[data-testid="stSidebar"] > div { padding-top: .5rem; }
section[data-testid="stSidebar"] * { color: #E9ECF2; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.16); margin: 1.4rem 0; }
.sb-marca { text-align: center; padding: .6rem 0 .2rem 0; }
.sb-marca .t { font-family: var(--serif); font-size: 2rem; letter-spacing: .14em; text-transform: uppercase;
  color: #FFFFFF; font-weight: 500; line-height: 1.1; }
.sb-marca .s { font-size: .68rem; letter-spacing: .38em; text-transform: uppercase; color: var(--ouro-claro) !important;
  font-weight: 700; margin-top: .9rem; }
.sb-secao { font-size: .72rem; letter-spacing: .34em; text-transform: uppercase; color: #C9CFDA !important;
  font-weight: 600; margin: .2rem 0 .7rem 0; }
.sb-rodape { font-size: 1.02rem; color: #F1F3F7 !important; margin-top: .3rem; }
.sb-status { font-size: .86rem; margin-top: .2rem; }
section[data-testid="stSidebar"] [role="radiogroup"] label p { font-size: 1.08rem; }
section[data-testid="stSidebar"] [role="radiogroup"] { gap: .55rem; }
/* Campos da barra lateral (seletores compatíveis com versões antigas e novas do Streamlit) */
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"],
section[data-testid="stSidebar"] [data-baseweb="input"],
section[data-testid="stSidebar"] [data-testid="stTextInputRootElement"] {
  background: var(--navy-2) !important; border: 1px solid rgba(255,255,255,.2) !important; border-radius: 10px !important; }
section[data-testid="stSidebar"] [data-baseweb="input"] > div,
section[data-testid="stSidebar"] [data-testid="stTextInputRootElement"] > div { background: transparent !important; }
section[data-testid="stSidebar"] input { background: transparent !important; color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF; }
section[data-testid="stSidebar"] input::placeholder { color: #9AA6BC !important; -webkit-text-fill-color: #9AA6BC; }
section[data-testid="stSidebar"] [data-testid="stSelectbox"] svg { fill: #C9CFDA; }
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-size: .9rem; color: #D6DBE5 !important; }

/* ---------------- Cabeçalhos ---------------- */
.eyebrow { color: var(--ouro); font-weight: 700; letter-spacing: .3em; font-size: .74rem; text-transform: uppercase; }
.pg-topo { display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
.pg-titulo { font-family: var(--serif); font-size: 3.3rem; font-weight: 500; color: var(--tinta); line-height: 1.1;
  margin: 1.1rem 0 .4rem 0; }
.pg-sub { color: var(--sutil); font-size: 1.05rem; margin: 1rem 0 0 0; }
.regua { border: none; border-top: 1px solid var(--regua); margin: 2.2rem 0 2.4rem 0; }
.sec-titulo { font-family: var(--serif); font-size: 2.45rem; font-weight: 500; color: var(--tinta); margin: 1.2rem 0 .2rem 0; }
.sec-sub { color: var(--texto); font-size: 1.02rem; margin: .9rem 0 1.6rem 0; }

.pill-status { border-radius: 999px; padding: .85rem 1.9rem; font-weight: 700; font-size: .95rem; white-space: nowrap;
  background: #F6EBD3; color: #6B4A10; border: 1px solid #E9D3A6; }
.pill-status.ok { background: #E3EFE7; color: var(--verde); border-color: #C4DCCB; }

/* ---------------- Cartões ---------------- */
div[class*="st-key-card"] { background: #FFFFFF; border: 1px solid var(--borda); border-radius: 18px;
  padding: 1.8rem 2.1rem; box-shadow: 0 12px 32px rgba(19,33,63,.06); }
.card-titulo { font-weight: 700; color: var(--navy); font-size: 1.12rem; margin-bottom: .3rem; }
.card-titulo .n { margin-right: .55rem; }
.vazio { text-align: center; color: var(--sutil); font-size: 1.05rem; padding: .6rem 0; }

/* ---------------- Pílulas ---------------- */
.pill { display: inline-block; border-radius: 999px; padding: .28rem .85rem; font-weight: 700; font-size: .8rem;
  border: 1px solid; margin: 0 .35rem .35rem 0; letter-spacing: .02em; }
.pill.vermelho { background: #F8E1DD; color: #8E2B1E; border-color: #EDC3BB; }
.pill.ambar { background: #F7EBCD; color: #7A5410; border-color: #EBD6A4; }
.pill.verde { background: #E1EFE6; color: var(--verde); border-color: #C4DCCB; }
.pill.azul { background: #E6ECF6; color: #26407A; border-color: #CBD6EA; }
.pill.neutro { background: #F1EEE7; color: #4A4F59; border-color: #E2DDD1; }
.contagem { display: inline-flex; align-items: center; margin-right: 1.1rem; }
.contagem b { font-size: 1.08rem; color: var(--tinta); margin-left: .1rem; }

/* ---------------- Classificação de risco ---------------- */
.risco { border-radius: 16px; padding: 2rem 2rem; height: 100%; min-height: 15rem; }
.risco.alto { background: #F7E3D9; color: var(--vermelho); }
.risco.medio { background: #F7ECD3; color: var(--ambar); }
.risco.baixo { background: #E3EFE6; color: var(--verde); }
.risco .r { font-size: .78rem; letter-spacing: .26em; text-transform: uppercase; font-weight: 700; }
.risco .v { font-family: var(--serif); font-size: 4.6rem; font-weight: 600; line-height: 1.05; margin: .2rem 0 .3rem 0; }
.risco .d { font-weight: 700; font-size: 1.02rem; }
.bloco-rot { font-weight: 800; font-size: .84rem; letter-spacing: .06em; text-transform: uppercase; color: #34466E;
  margin: 0 0 .55rem 0; }
.bloco-rot.mt { margin-top: 1.3rem; }
.marcadores { margin: 0 0 0 1.2rem; padding: 0; }
.marcadores li { margin: .2rem 0; font-size: 1.04rem; color: var(--tinta); }

/* ---------------- Métricas ---------------- */
.metricas { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 1.5rem; margin: .4rem 0 0 0; }
@media (max-width: 900px) { .metricas { grid-template-columns: repeat(2, minmax(0,1fr)); } }
.metricas .r { font-weight: 700; color: var(--tinta); font-size: 1.06rem; }
.metricas .v { font-size: 2.7rem; font-weight: 800; color: var(--navy); line-height: 1.25; }

/* ---------------- Listas ---------------- */
.lista { list-style: none; padding: 0; margin: 0; }
.lista li { padding: .7rem 0; border-bottom: 1px solid #EFEBE3; display: flex; gap: .8rem; align-items: flex-start; }
.lista li:last-child { border-bottom: none; }
.lista .ico { flex: 0 0 auto; width: 24px; height: 24px; border-radius: 50%; display: inline-flex; align-items: center;
  justify-content: center; font-size: .78rem; font-weight: 800; margin-top: 1px; }
.ico.ok { background: #E1EFE6; color: var(--verde); }
.ico.alerta { background: #F7EBCD; color: #7A5410; }
.ico.erro { background: #F8E1DD; color: #8E2B1E; }
.ico.info { background: #E6ECF6; color: #26407A; }
.lista .dir { margin-left: auto; }
.sutil { color: var(--sutil); font-size: .88rem; }

.recomendacao { border-left: 4px solid var(--ouro); background: var(--creme-2); border-radius: 0 12px 12px 0;
  padding: 1.1rem 1.4rem; margin: 1.2rem 0; }
.recomendacao .t { font-size: .74rem; letter-spacing: .28em; text-transform: uppercase; color: var(--ouro); font-weight: 700; }
.recomendacao .x { font-family: var(--serif); font-size: 1.55rem; font-weight: 600; color: var(--tinta); margin-top: .25rem;
  line-height: 1.25; }
.aviso { font-size: .8rem; color: var(--sutil); margin-top: 1.4rem; }

/* ---------------- Widgets ---------------- */
.stButton > button, .stDownloadButton > button {
  background: #FFFFFF; color: var(--navy); border: 1.5px solid var(--navy); border-radius: 10px;
  padding: .75rem 1.6rem; font-weight: 700; transition: all .15s ease; }
.stButton > button:hover, .stDownloadButton > button:hover { background: var(--navy); color: #FFFFFF; border-color: var(--navy); }
.stButton > button[kind="primary"] { background: var(--navy); color: #FFFFFF; }
.stButton > button[kind="primary"]:hover { background: var(--navy-2); }
.stButton > button:disabled { opacity: .45; }

div[data-testid="stFileUploader"] section { border: 1px dashed #D3C8B3; background: var(--creme-2); border-radius: 12px; }
.stTabs [role="tablist"] { gap: 2rem; }
.stTabs [role="tab"] { padding: .7rem 0; }
.stTabs [role="tab"] p { font-size: 1.06rem !important; font-weight: 600; color: var(--sutil); }
.stTabs [role="tab"][aria-selected="true"] p { color: var(--tinta); }

div[class*="st-key-sel_caso"] [data-baseweb="select"] > div,
div[class*="st-key-sel_caso"] [data-testid="stSelectbox"] [role="group"] {
  background: #23262D !important; border: none !important; border-radius: 10px !important; min-height: 3.4rem; }
div[class*="st-key-sel_caso"] [data-baseweb="select"] *,
div[class*="st-key-sel_caso"] [role="group"] input { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF;
  font-size: 1.05rem !important; background: transparent !important; }
div[class*="st-key-sel_caso"] [role="group"] svg { fill: #FFFFFF; }
div[class*="st-key-sel_caso"] label p { font-size: 1.08rem; color: var(--tinta); }

.tabela { width: 100%; border-collapse: collapse; }
.tabela th { text-align: left; font-size: .8rem; letter-spacing: .08em; text-transform: uppercase; color: #34466E;
  padding: .4rem .6rem .8rem .6rem; border-bottom: 1px solid var(--regua); }
.tabela td { padding: .8rem .6rem; border-bottom: 1px solid #EFEBE3; vertical-align: top; }
.tabela tr:last-child td { border-bottom: none; }
[data-testid="stExpander"] details { background: #FFFFFF; border: 1px solid var(--borda); border-radius: 12px; }
[data-testid="stDataFrame"] { border: 1px solid var(--borda); border-radius: 10px; }
</style>
"""


def aplicar_estilos() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
