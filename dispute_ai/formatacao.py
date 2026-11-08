"""Funções de formatação no padrão brasileiro."""

from __future__ import annotations

from datetime import datetime


def moeda(valor: float | None) -> str:
    if valor is None:
        return "Não identificado"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_hora(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return iso or ""


ROTULOS_CAMPOS = {
    "valor": "Valor",
    "data": "Data da transação",
    "estabelecimento": "Estabelecimento",
    "cnpj": "CNPJ",
    "titular": "Titular / comprador",
    "cartao_final": "Cartão (final)",
    "bandeira": "Bandeira",
    "nsu": "NSU",
    "codigo_autorizacao": "Código de autorização",
    "canal": "Canal",
    "produto": "Produto / serviço",
}


def rotulo_campo(chave: str) -> str:
    return ROTULOS_CAMPOS.get(chave, chave.replace("_", " ").capitalize())


def valor_campo(chave: str, valor) -> str:
    if chave == "valor" and isinstance(valor, (int, float)):
        return moeda(float(valor))
    if chave == "cartao_final" and valor:
        return f"•••• {valor}"
    if isinstance(valor, list):
        return ", ".join(str(v) for v in valor)
    return str(valor)
