"""Gera os documentos fictícios do CASO DEMONSTRATIVO (venda de R$ 850,00 contestada).

Uso:
    python scripts/gerar_exemplos.py

Os arquivos são criados na pasta ``exemplos/``. TODOS OS DADOS SÃO FICTÍCIOS.
De propósito, o conjunto NÃO inclui comprovante de entrega, para que a análise
aponte essa lacuna.
"""

from __future__ import annotations

import io
import sys
from email.message import EmailMessage
from pathlib import Path

import pymupdf

PASTA = Path(__file__).resolve().parent.parent / "exemplos"

CSS = """
* { font-family: sans-serif; }
body { font-size: 10pt; color: #1F2937; }
h1 { font-size: 15pt; color: #0B2545; margin: 0 0 4pt 0; }
.sub { color: #64748B; font-size: 9pt; }
table { width: 100%; border-collapse: collapse; margin-top: 8pt; }
td, th { border: 1px solid #CBD5E1; padding: 4pt 6pt; text-align: left; }
th { background-color: #EEF2F7; }
.ficticio { color: #B91C1C; font-weight: bold; font-size: 8pt; margin-top: 14pt; }
.box { border: 1px solid #CBD5E1; padding: 8pt; margin-top: 8pt; }
"""

RODAPE = "<p class='ficticio'>DOCUMENTO FICTÍCIO — gerado para demonstração do Dispute AI.</p>"


def html_para_pdf(html: str, tamanho: str = "a4") -> bytes:
    story = pymupdf.Story(html=html + RODAPE, user_css=CSS)
    pagina = pymupdf.paper_rect(tamanho)
    buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(buffer)
    mais = True
    while mais:
        dev = writer.begin_page(pagina)
        mais, _ = story.place(pagina + (36, 36, -36, -36))
        story.draw(dev)
        writer.end_page()
    writer.close()
    return buffer.getvalue()


NOTIFICACAO = """
<h1>Notificação de Contestação (Chargeback)</h1>
<p class="sub">Adquirente Exemplo Pagamentos S.A. · Central de Disputas</p>
<table>
<tr><th>Protocolo da disputa</th><td>DSP-2026-000123</td></tr>
<tr><th>Data da notificação</th><td>03/11/2026</td></tr>
<tr><th>Estabelecimento</th><td>Loja Exemplo Eletrônicos Ltda</td></tr>
<tr><th>CNPJ</th><td>12.345.678/0001-90</td></tr>
<tr><th>Data da transação</th><td>14/10/2026</td></tr>
<tr><th>Valor contestado</th><td>R$ 850,00</td></tr>
<tr><th>Cartão</th><td>VISA **** 4821</td></tr>
<tr><th>NSU</th><td>004512873</td></tr>
<tr><th>Código do motivo</th><td>10.4</td></tr>
<tr><th>Motivo informado</th><td>Compra não reconhecida pelo titular do cartão</td></tr>
</table>
<div class="box">
<p>O titular do cartão informou ao banco emissor que não reconhece a transação acima.
Para contestar o chargeback, o estabelecimento deve apresentar evidências que comprovem
a legitimidade da venda, tais como nota fiscal, comprovante de entrega assinado,
registros de autenticação e comunicações com o comprador.</p>
<p><b>Prazo para apresentação da defesa: 18/11/2026.</b> A ausência de resposta implica
aceite do chargeback e débito do valor na agenda de recebíveis.</p>
</div>
"""

COMPROVANTE = """
<h1>Comprovante de Pagamento</h1>
<p class="sub">Via do cliente · Pagamento aprovado</p>
<table>
<tr><th>Estabelecimento</th><td>Loja Exemplo Eletrônicos Ltda</td></tr>
<tr><th>CNPJ</th><td>12.345.678/0001-90</td></tr>
<tr><th>Data/hora</th><td>14/10/2026 21:47:12</td></tr>
<tr><th>Forma de pagamento</th><td>Crédito à vista (1x de R$ 850,00)</td></tr>
<tr><th>Cartão</th><td>VISA **** 4821</td></tr>
<tr><th>Titular</th><td>Mariana Souza Lima</td></tr>
<tr><th>NSU</th><td>004512873</td></tr>
<tr><th>Código de autorização</th><td>A7K29Q</td></tr>
<tr><th>Valor total</th><td>R$ 850,00</td></tr>
</table>
"""

REGISTRO = """
<h1>Registro da Transação</h1>
<p class="sub">Log do gateway de pagamentos · Exportado em 04/11/2026</p>
<table>
<tr><th>ID da transação</th><td>TRX-88AF-2026-1014-0091</td></tr>
<tr><th>Data/hora (UTC-3)</th><td>14/10/2026 21:47:12</td></tr>
<tr><th>Canal</th><td>E-commerce (cartão não presente)</td></tr>
<tr><th>Valor</th><td>R$ 850,00</td></tr>
<tr><th>Bandeira</th><td>VISA</td></tr>
<tr><th>Cartão</th><td>**** 4821</td></tr>
<tr><th>NSU</th><td>004512873</td></tr>
<tr><th>Código de autorização</th><td>A7K29Q</td></tr>
<tr><th>Status</th><td>Aprovada / Capturada</td></tr>
<tr><th>Autenticação 3DS</th><td>Não realizada</td></tr>
<tr><th>IP do comprador</th><td>189.40.xxx.xxx (São Paulo/SP)</td></tr>
<tr><th>Análise antifraude</th><td>Score 62/100 — aprovado com ressalva</td></tr>
<tr><th>Endereço de entrega</th><td>Rua das Acácias, 120 — Campinas/SP</td></tr>
</table>
"""

NOTA_FISCAL = """
<h1>DANFE — Nota Fiscal Eletrônica (NF-e)</h1>
<p class="sub">Documento auxiliar da nota fiscal eletrônica · Nº 000.045.219 · Série 1</p>
<table>
<tr><th>Emitente</th><td>Loja Exemplo Eletrônicos Ltda — CNPJ 12.345.678/0001-90</td></tr>
<tr><th>Destinatário</th><td>Mariana Souza Lima</td></tr>
<tr><th>Endereço</th><td>Rua das Acácias, 120 — Campinas/SP</td></tr>
<tr><th>Data de emissão</th><td>14/10/2026</td></tr>
<tr><th>Chave de acesso</th><td>3526 1012 3456 7800 0190 5500 1000 0452 1910 0045 2190</td></tr>
</table>
<table>
<tr><th>Produto</th><th>Qtd.</th><th>Valor unitário</th><th>Valor total</th></tr>
<tr><td>Fone de ouvido Bluetooth XP-500</td><td>1</td><td>R$ 850,00</td><td>R$ 850,00</td></tr>
</table>
<table>
<tr><th>Frete</th><td>R$ 0,00 (grátis)</td><th>Valor total da nota</th><td>R$ 850,00</td></tr>
</table>
"""

STATUS_PEDIDO = """
<h1>Minha conta › Pedido #55102</h1>
<p class="sub">Captura de tela do painel da loja — 04/11/2026</p>
<table>
<tr><th>Pedido</th><td>#55102 — Fone de ouvido Bluetooth XP-500</td></tr>
<tr><th>Valor</th><td>R$ 850,00</td></tr>
<tr><th>Pagamento</th><td>Aprovado em 14/10/2026</td></tr>
<tr><th>Envio</th><td>Postado em 15/10/2026 — Transportadora Exemplo</td></tr>
<tr><th>Situação</th><td>Em trânsito — sem confirmação de recebimento</td></tr>
</table>
"""

ATENDIMENTO = """Histórico de atendimento — Loja Exemplo Eletrônicos
Pedido: #55102
Canal: chat do site

[05/11/2026 10:12] Atendente (Paulo): Olá! Recebemos um aviso do banco sobre o pedido #55102.
Poderia confirmar se reconhece a compra do fone de ouvido XP-500?
[05/11/2026 10:30] Sem resposta da cliente.
[06/11/2026 09:05] Atendente (Paulo): Nova tentativa de contato por telefone (19) 9xxxx-xxxx — chamada não atendida.
[06/11/2026 09:07] Observação interna: pedido postado em 15/10/2026. A transportadora ainda não
enviou o comprovante de recebimento assinado. Solicitado ao setor de logística.
"""


def gerar_eml() -> bytes:
    msg = EmailMessage()
    msg["From"] = "Loja Exemplo Eletrônicos <pedidos@loja-exemplo.com.br>"
    msg["To"] = "Mariana Souza Lima <mariana.lima@email-exemplo.com.br>"
    msg["Date"] = "Wed, 14 Oct 2026 21:49:03 -0300"
    msg["Subject"] = "Confirmação do pedido #55102 — pagamento aprovado"
    msg.set_content(
        "Olá, Mariana!\n\n"
        "Recebemos o seu pedido #55102 e o pagamento foi aprovado.\n\n"
        "Produto: Fone de ouvido Bluetooth XP-500\n"
        "Valor: R$ 850,00 (crédito à vista, cartão final 4821)\n"
        "Endereço de entrega: Rua das Acácias, 120 — Campinas/SP\n"
        "Prazo estimado de entrega: até 22/10/2026\n\n"
        "Você receberá o código de rastreamento assim que o pedido for postado.\n\n"
        "Atenciosamente,\nEquipe Loja Exemplo\n\n"
        "-- E-mail fictício gerado para demonstração do Dispute AI --"
    )
    return msg.as_bytes()


def gerar_png(html: str) -> bytes:
    pdf = pymupdf.open("pdf", html_para_pdf(html, "a5-l"))
    pix = pdf[0].get_pixmap(dpi=110)
    return pix.tobytes("png")


def main() -> None:
    PASTA.mkdir(exist_ok=True)
    arquivos = {
        "01_notificacao_contestacao.pdf": html_para_pdf(NOTIFICACAO),
        "02_comprovante_pagamento.pdf": html_para_pdf(COMPROVANTE, "a5"),
        "03_registro_transacao.pdf": html_para_pdf(REGISTRO),
        "04_nota_fiscal.pdf": html_para_pdf(NOTA_FISCAL),
        "05_email_confirmacao_pedido.eml": gerar_eml(),
        "06_historico_atendimento.txt": ATENDIMENTO.encode("utf-8"),
        "07_print_status_pedido.png": gerar_png(STATUS_PEDIDO),
    }
    for nome, dados in arquivos.items():
        (PASTA / nome).write_bytes(dados)
        print(f"  ✓ {nome} ({len(dados) / 1024:.1f} KB)")
    print(f"\n{len(arquivos)} documentos fictícios gerados em: {PASTA}")


if __name__ == "__main__":
    sys.exit(main())
