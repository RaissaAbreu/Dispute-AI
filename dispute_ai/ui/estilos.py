"""Estilo visual corporativo (azul-escuro) aplicado à interface Streamlit."""

import streamlit as st

CSS = """
<style>
:root {
  --navy: #0B2545; --azul: #1D4E89; --azul-claro: #EAF1FB; --borda: #DCE3EC;
  --texto: #1F2937; --sutil: #64748B; --verde: #047857; --ambar: #B45309; --vermelho: #B91C1C;
}
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 3.5rem; max-width: 1200px; }

section[data-testid="stSidebar"] { background: var(--navy); }
section[data-testid="stSidebar"] * { color: #E6EDF6; }
section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] [data-baseweb="select"] * {
  color: var(--texto) !important;
}
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.15); }

.da-marca { display:flex; align-items:center; gap:.6rem; margin-bottom:.25rem; }
.da-logo { width:36px; height:36px; border-radius:9px; background:linear-gradient(135deg,#3E7CC4,#1D4E89);
  display:flex; align-items:center; justify-content:center; font-weight:800; color:#fff; font-size:15px; }
.da-nome { font-size:1.2rem; font-weight:700; color:#fff; line-height:1.1; }
.da-slogan { font-size:.75rem; color:#9FB4CF !important; }

.da-hero { background: linear-gradient(120deg, var(--navy) 0%, var(--azul) 100%); color:#fff;
  border-radius: 14px; padding: 1.4rem 1.6rem; margin-bottom: 1.2rem; }
.da-hero h1 { color:#fff; font-size:1.55rem; margin:0 0 .25rem 0; padding:0; }
.da-hero p { color:#C9D8EC; margin:0; font-size:.95rem; }

.da-card { background:#fff; border:1px solid var(--borda); border-radius:12px; padding:1rem 1.2rem;
  margin-bottom: .9rem; }
.da-card h4 { margin:0 0 .6rem 0; color:var(--navy); font-size:1rem; }

.da-caso-topo { display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:.5rem; }
.da-rotulo { font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; color:var(--sutil); }
.da-caso-num { font-size:1.5rem; font-weight:800; color:var(--navy); }

.da-badge { display:inline-block; padding:.28rem .7rem; border-radius:999px; font-size:.8rem; font-weight:700; }
.da-badge.revisao { background:#FEF3C7; color:var(--ambar); }
.da-badge.suficiente { background:#D1FAE5; color:var(--verde); }
.da-badge.insuficiente { background:#FEE2E2; color:var(--vermelho); }
.da-chip { display:inline-block; padding:.12rem .55rem; border-radius:6px; font-size:.72rem; font-weight:600;
  background:var(--azul-claro); color:var(--azul); margin-right:.3rem; }
.da-chip.forte { background:#D1FAE5; color:var(--verde); }
.da-chip.moderada { background:#E0E7FF; color:#3730A3; }
.da-chip.fraca { background:#F1F5F9; color:var(--sutil); }

.da-kpis { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:.75rem; margin:.4rem 0 1rem 0; }
@media (max-width: 800px) { .da-kpis { grid-template-columns: repeat(2, minmax(0,1fr)); } }
.da-kpi { background:#fff; border:1px solid var(--borda); border-radius:12px; padding:.8rem 1rem; }
.da-kpi .v { font-size:1.25rem; font-weight:800; color:var(--navy); margin-top:.15rem; }
.da-kpi .v.alto { color:var(--vermelho); } .da-kpi .v.medio { color:var(--ambar); } .da-kpi .v.baixo { color:var(--verde); }

.da-lista { list-style:none; padding:0; margin:0; }
.da-lista li { padding:.45rem 0; border-bottom:1px solid #EEF2F7; display:flex; gap:.55rem; align-items:flex-start; }
.da-lista li:last-child { border-bottom:none; }
.da-ico { flex:0 0 auto; width:20px; height:20px; border-radius:50%; display:inline-flex; align-items:center;
  justify-content:center; font-size:.72rem; font-weight:800; margin-top:1px; }
.da-ico.ok { background:#D1FAE5; color:var(--verde); }
.da-ico.alerta { background:#FEF3C7; color:var(--ambar); }
.da-ico.erro { background:#FEE2E2; color:var(--vermelho); }
.da-ico.info { background:var(--azul-claro); color:var(--azul); }
.da-sub { color:var(--sutil); font-size:.82rem; }

.da-rec { background:var(--azul-claro); border-left:5px solid var(--azul); border-radius:10px;
  padding:1rem 1.2rem; margin-bottom:.9rem; }
.da-rec .t { font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:var(--azul); font-weight:700; }
.da-rec .r { font-size:1.05rem; font-weight:700; color:var(--navy); margin-top:.2rem; }

.da-aviso { font-size:.78rem; color:var(--sutil); margin-top:.5rem; }
div[data-testid="stFileUploader"] section { border:2px dashed #B6C6DA; background:#F8FAFD; border-radius:12px; }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  background: var(--azul); border-color: var(--azul); }
</style>
"""


def aplicar_estilos() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
