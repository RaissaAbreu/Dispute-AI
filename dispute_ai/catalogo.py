"""Catálogo de tipos de documento, motivos de contestação e checklist de evidências.

Este módulo é a "fonte da verdade" de regras de negócio: tanto o modo com LLM quanto o
modo demonstração usam o mesmo checklist para apontar documentos ausentes, garantindo
resultados consistentes e auditáveis.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Tipos de documento
# ---------------------------------------------------------------------------
TIPOS_DOCUMENTO: dict[str, str] = {
    "comprovante_pagamento": "Comprovante de pagamento",
    "registro_transacao": "Registro da transação",
    "nota_fiscal": "Nota fiscal",
    "comprovante_entrega": "Comprovante de entrega",
    "comunicacao_cliente": "Comunicação com o cliente",
    "notificacao_contestacao": "Notificação de contestação",
    "autenticacao_3ds": "Autenticação 3DS / dados do dispositivo",
    "politica_cancelamento": "Política de cancelamento / termos",
    "comprovante_reembolso": "Comprovante de estorno / reembolso",
    "contrato_termos": "Contrato / aceite de termos",
    "outro": "Outro documento",
}

# ---------------------------------------------------------------------------
# Motivos de contestação
# ---------------------------------------------------------------------------
MOTIVOS: dict[str, str] = {
    "nao_reconhecida": "Compra não reconhecida",
    "nao_recebido": "Produto/serviço não recebido",
    "divergente": "Produto/serviço divergente ou com defeito",
    "cancelamento": "Cancelamento ou reembolso não processado",
    "duplicidade": "Cobrança em duplicidade",
    "valor_incorreto": "Valor cobrado incorreto",
    "outro": "Outro motivo",
}

# Checklist: para cada motivo, documentos obrigatórios e recomendados, com a justificativa.
CHECKLIST: dict[str, dict[str, dict[str, str]]] = {
    "nao_reconhecida": {
        "obrigatorios": {
            "registro_transacao": "Comprova dados da autorização (NSU, código, data e hora).",
            "comprovante_pagamento": "Demonstra a efetivação do pagamento.",
            "nota_fiscal": "Vincula a transação a uma venda real de produto/serviço.",
            "comprovante_entrega": "Demonstra que o produto foi entregue ao titular ou no endereço informado.",
        },
        "recomendados": {
            "autenticacao_3ds": "Autenticação do portador (3DS, IP, dispositivo) reforça a legitimidade.",
            "comunicacao_cliente": "Contatos com o comprador ajudam a demonstrar reconhecimento da compra.",
        },
    },
    "nao_recebido": {
        "obrigatorios": {
            "registro_transacao": "Comprova dados da autorização.",
            "nota_fiscal": "Identifica o produto e o endereço de entrega.",
            "comprovante_entrega": "Prova central para este motivo: rastreio com assinatura/data de entrega.",
        },
        "recomendados": {
            "comunicacao_cliente": "Mostra tratativas e prazos informados ao cliente.",
        },
    },
    "divergente": {
        "obrigatorios": {
            "nota_fiscal": "Descreve o produto efetivamente vendido.",
            "comprovante_entrega": "Comprova a entrega do item.",
            "comunicacao_cliente": "Registra a reclamação e a tratativa oferecida.",
        },
        "recomendados": {
            "politica_cancelamento": "Política de trocas/devoluções aceita pelo cliente.",
            "registro_transacao": "Comprova dados da autorização.",
        },
    },
    "cancelamento": {
        "obrigatorios": {
            "registro_transacao": "Comprova dados da autorização.",
            "politica_cancelamento": "Regras de cancelamento informadas e aceitas pelo cliente.",
            "comunicacao_cliente": "Registra a solicitação (ou ausência) de cancelamento.",
        },
        "recomendados": {
            "comprovante_reembolso": "Se houve estorno, comprova o valor e a data.",
            "contrato_termos": "Aceite de termos de serviço/assinatura.",
        },
    },
    "duplicidade": {
        "obrigatorios": {
            "registro_transacao": "Registros de todas as transações envolvidas, para distinguir cobranças.",
            "nota_fiscal": "Demonstra se houve uma ou mais vendas distintas.",
        },
        "recomendados": {
            "comprovante_pagamento": "Comprovantes de cada cobrança.",
            "comprovante_reembolso": "Se uma cobrança foi estornada, comprovar.",
        },
    },
    "valor_incorreto": {
        "obrigatorios": {
            "nota_fiscal": "Mostra o valor acordado na venda.",
            "registro_transacao": "Mostra o valor efetivamente autorizado.",
        },
        "recomendados": {
            "comprovante_pagamento": "Valor apresentado ao portador no momento da compra.",
            "comunicacao_cliente": "Acordos de preço, descontos ou parcelamento.",
        },
    },
    "outro": {
        "obrigatorios": {
            "registro_transacao": "Comprova dados da autorização.",
            "nota_fiscal": "Vincula a transação a uma venda real.",
        },
        "recomendados": {
            "comunicacao_cliente": "Contexto adicional da relação com o cliente.",
        },
    },
}

STATUS = {
    "revisao": "Revisão necessária",
    "suficiente": "Evidências suficientes",
    "insuficiente": "Evidências insuficientes",
}

NIVEIS_RISCO = {"baixo": "Baixo", "medio": "Médio", "alto": "Alto"}


def rotulo_tipo(tipo: str) -> str:
    return TIPOS_DOCUMENTO.get(tipo, TIPOS_DOCUMENTO["outro"])


def rotulo_motivo(motivo: str) -> str:
    return MOTIVOS.get(motivo, MOTIVOS["outro"])


def avaliar_checklist(motivo: str, tipos_presentes: set[str]) -> dict:
    """Compara os tipos de documento presentes com o checklist do motivo."""
    regra = CHECKLIST.get(motivo, CHECKLIST["outro"])
    itens = []
    for categoria in ("obrigatorios", "recomendados"):
        for tipo, justificativa in regra[categoria].items():
            itens.append(
                {
                    "tipo": tipo,
                    "documento": rotulo_tipo(tipo),
                    "obrigatorio": categoria == "obrigatorios",
                    "presente": tipo in tipos_presentes,
                    "justificativa": justificativa,
                }
            )
    ausentes = [i for i in itens if not i["presente"]]
    return {
        "itens": itens,
        "ausentes_obrigatorios": [i for i in ausentes if i["obrigatorio"]],
        "ausentes_recomendados": [i for i in ausentes if not i["obrigatorio"]],
        "cobertura": round(100 * sum(i["presente"] for i in itens if i["obrigatorio"])
                           / max(1, sum(1 for i in itens if i["obrigatorio"]))),
    }
