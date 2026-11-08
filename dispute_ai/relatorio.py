"""Geração do relatório da análise em PDF, usando PyMuPDF (Story + DocumentWriter)."""

from __future__ import annotations

import io
from html import escape

import pymupdf

from .catalogo import rotulo_tipo
from .formatacao import moeda, rotulo_campo, valor_campo

CORES_STATUS = {"revisao": ("#B45309", "#FEF3C7"), "suficiente": ("#047857", "#D1FAE5"),
                "insuficiente": ("#B91C1C", "#FEE2E2")}
CORES_RISCO = {"baixo": "#047857", "medio": "#B45309", "alto": "#B91C1C"}

CSS = """
* { font-family: sans-serif; }
body { font-size: 9.5pt; color: #1F2937; }
h2 { font-size: 11.5pt; color: #0B2545; margin: 14pt 0 5pt 0; padding-bottom: 3pt;
     border-bottom: 1px solid #CBD5E1; }
p { margin: 0 0 4pt 0; line-height: 1.35; }
table { width: 100%; border-collapse: collapse; }
td, th { padding: 4pt 6pt; vertical-align: top; text-align: left; }
.caso { font-size: 13pt; font-weight: bold; color: #0B2545; margin: 10pt 0 2pt 0; }
.kpi td { border: 1px solid #CBD5E1; }
.kpi-r { font-size: 7.5pt; color: #64748B; text-transform: uppercase; }
.kpi-v { font-size: 11pt; font-weight: bold; color: #0B2545; }
.grade td, .grade th { border-bottom: 1px solid #E2E8F0; }
.grade th { background-color: #EEF2F7; color: #0B2545; font-size: 8.5pt; }
.rot { color: #64748B; }
ul { margin: 0 0 0 14pt; padding: 0; }
li { margin-bottom: 2pt; }
.rec td { border: 1px solid #1D4E89; border-left: 4px solid #1D4E89; color: #0B2545; }
.alerta { color: #B91C1C; }
.ok { color: #047857; }
.aviso { font-size: 7.5pt; color: #64748B; margin-top: 12pt; }
"""


def _lista(itens: list[str], vazio: str = "Nenhum item.") -> str:
    if not itens:
        return f"<p>{escape(vazio)}</p>"
    return "<ul>" + "".join(f"<li>{escape(i)}</li>" for i in itens) + "</ul>"


def montar_html(analise: dict) -> str:
    meta = analise.get("meta", {})
    transacao = analise.get("transacao", {})
    motivo = analise.get("motivo", {})
    status = analise.get("status", "revisao")
    cor_txt, _ = CORES_STATUS.get(status, CORES_STATUS["revisao"])
    risco = analise.get("nivel_risco", "medio")
    numero = analise.get("numero", "")

    linhas_transacao = "".join(
        f"<tr><td class='rot' width='32%'>{escape(rotulo_campo(k))}</td><td>{escape(valor_campo(k, v))}</td></tr>"
        for k, v in transacao.items()
    ) or "<tr><td>Nenhum dado identificado.</td></tr>"

    evidencias = [f"{e['descricao']} ({e.get('forca', '')}) — {e.get('arquivo', '')}"
                  for e in analise.get("evidencias", [])]
    ausentes = [f"{d['documento']}{' (obrigatório)' if d['obrigatorio'] else ' (recomendado)'}: "
                f"{d['justificativa']}" for d in analise.get("documentos_ausentes", [])]

    docs = "".join(
        f"<tr><td>{escape(d['arquivo'])}</td><td>{escape(rotulo_tipo(d['tipo']))}</td>"
        f"<td>{escape(d.get('resumo', ''))}</td></tr>"
        for d in analise.get("documentos", [])
    )
    providencias = "".join(f"<li>{escape(p)}</li>" for p in analise.get("providencias", []))
    motivo_txt = motivo.get("descricao") or motivo.get("rotulo", "")
    extras_motivo = []
    if motivo.get("codigo"):
        extras_motivo.append(f"Código do motivo: {motivo['codigo']}")
    if motivo.get("prazo_resposta"):
        extras_motivo.append(f"Prazo de resposta: {motivo['prazo_resposta']}")

    decisao = ""
    if analise.get("notas_analista") or analise.get("decisao_analista") not in (None, "pendente"):
        from .banco import DECISOES
        decisao = (f"<h2>Parecer do analista</h2><p><b>Decisão:</b> "
                   f"{escape(DECISOES.get(analise.get('decisao_analista', 'pendente'), ''))}</p>"
                   f"<p>{escape(analise.get('notas_analista') or '')}</p>")

    return f"""
<p class="caso">CASO {escape(numero)}</p>
<p style="color:{cor_txt}; font-weight:bold;">● {escape(analise.get('status_rotulo', ''))}</p>

<table class="kpi" style="margin-top:8pt"><tr>
 <td><span class="kpi-r">Valor contestado</span><br/><span class="kpi-v">{escape(moeda(transacao.get('valor')))}</span></td>
 <td><span class="kpi-r">Motivo</span><br/><span class="kpi-v">{escape(motivo.get('rotulo', ''))}</span></td>
 <td><span class="kpi-r">Risco de perda</span><br/><span class="kpi-v" style="color:{CORES_RISCO.get(risco, '#0B2545')}">{escape(analise.get('nivel_risco_rotulo', ''))}</span></td>
 <td><span class="kpi-r">Cobertura de evidências</span><br/><span class="kpi-v">{analise.get('checklist', {}).get('cobertura', 0)}%</span></td>
</tr></table>

<h2>Resumo</h2>
<p>{escape(analise.get('resumo', ''))}</p>

<h2>Motivo informado</h2>
<p>{escape(motivo_txt)}</p>
{''.join(f'<p>{escape(x)}</p>' for x in extras_motivo)}

<h2>Dados da transação</h2>
<table class="grade">{linhas_transacao}</table>

<h2>Evidências identificadas</h2>
{_lista(evidencias, 'Nenhuma evidência identificada.')}

<h2>Pontos de atenção</h2>
{_lista(analise.get('pontos_atencao', []), 'Nenhum ponto de atenção.')}

<h2>Inconsistências</h2>
{_lista(analise.get('inconsistencias', []), 'Nenhuma inconsistência identificada entre os documentos.')}

<h2>Documentos ausentes</h2>
{_lista(ausentes, 'Todos os documentos do checklist foram apresentados.')}

<h2>Documentos analisados</h2>
<table class="grade"><tr><th width="34%">Arquivo</th><th width="22%">Tipo</th><th>Conteúdo</th></tr>{docs}</table>

<h2>Recomendação da IA</h2>
<table class="rec"><tr><td><b>{escape(analise.get('recomendacao', ''))}</b></td></tr></table>

<h2>Providências sugeridas</h2>
<ol>{providencias}</ol>
{decisao}
<p class="aviso">{escape(analise.get('aviso_legal', ''))} Documentos e dados deste caso são fictícios
quando utilizados para demonstração.</p>
"""


ALTURA_CABECALHO = 62
AZUL_ESCURO = (11 / 255, 37 / 255, 69 / 255)
AZUL_CLARO = (191 / 255, 211 / 255, 234 / 255)


def _desenhar_cabecalho(pagina: pymupdf.Page, analise: dict) -> None:
    """Faixa azul-escura com a marca, desenhada diretamente (fora do fluxo HTML)."""
    meta = analise.get("meta", {})
    largura = pagina.rect.width
    pagina.draw_rect(pymupdf.Rect(0, 0, largura, 82), color=None, fill=AZUL_ESCURO)
    pagina.insert_text((40, 42), "Dispute AI", fontsize=18, fontname="hebo", color=(1, 1, 1))
    pagina.insert_text((40, 60), "Análise de contestação · relatório preliminar",
                       fontsize=9, fontname="helv", color=AZUL_CLARO)
    origem = meta.get("provedor_nome", "")
    if meta.get("modelo"):
        origem += f" · {meta['modelo']}"
    for y, texto in ((42, f"Gerado em {meta.get('gerado_em', '')}"), (58, origem)):
        w = pymupdf.get_text_length(texto, fontname="helv", fontsize=8.5)
        pagina.insert_text((largura - 40 - w, y), texto, fontsize=8.5, fontname="helv", color=AZUL_CLARO)


def gerar_pdf(analise: dict) -> bytes:
    """Renderiza o relatório em PDF (A4) e devolve os bytes."""
    story = pymupdf.Story(html=montar_html(analise), user_css=CSS)
    pagina = pymupdf.paper_rect("a4")
    area = pagina + (40, 40, -40, -50)
    buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(buffer)
    mais, primeira = True, True
    while mais:
        dispositivo = writer.begin_page(pagina)
        # Na primeira página, reserva espaço para o cabeçalho desenhado depois.
        mais, _ = story.place(area + (0, ALTURA_CABECALHO, 0, 0) if primeira else area)
        primeira = False
        story.draw(dispositivo)
        writer.end_page()
    writer.close()

    doc = pymupdf.open("pdf", buffer.getvalue())
    _desenhar_cabecalho(doc[0], analise)

    # Rodapé com numeração de páginas.
    total = doc.page_count
    for i, pg in enumerate(doc, start=1):
        texto = f"Dispute AI · Caso {analise.get('numero', '')} · Página {i} de {total}"
        pg.insert_text((40, pagina.height - 25), texto, fontsize=7.5, color=(0.39, 0.45, 0.55))
    dados = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return dados
