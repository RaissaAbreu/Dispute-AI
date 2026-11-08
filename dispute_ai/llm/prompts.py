"""Prompts usados na análise por LLM."""

from __future__ import annotations

import json

from ..catalogo import CHECKLIST, MOTIVOS, TIPOS_DOCUMENTO

ESQUEMA_RESPOSTA = {
    "resumo": "string — síntese objetiva do caso em 2 a 4 frases",
    "transacao": {
        "valor": "number | null — valor contestado em reais (ex.: 850.0)",
        "data": "string | null — data da transação (DD/MM/AAAA)",
        "estabelecimento": "string | null",
        "cnpj": "string | null",
        "titular": "string | null — nome do portador/comprador",
        "cartao_final": "string | null — 4 últimos dígitos",
        "bandeira": "string | null",
        "nsu": "string | null",
        "codigo_autorizacao": "string | null",
        "canal": "string | null — ex.: e-commerce, presencial",
        "produto": "string | null — descrição do produto/serviço",
    },
    "motivo": {
        "categoria": "uma das chaves: " + ", ".join(MOTIVOS),
        "descricao": "string — motivo conforme informado na contestação",
        "codigo": "string | null — código de motivo (reason code), se houver",
        "prazo_resposta": "string | null — prazo para apresentar defesa, se informado",
    },
    "documentos": [
        {
            "arquivo": "string — nome exato do arquivo recebido",
            "tipo": "uma das chaves: " + ", ".join(TIPOS_DOCUMENTO),
            "resumo": "string — o que o documento comprova",
            "dados_extraidos": "objeto chave→valor com os principais dados lidos",
        }
    ],
    "evidencias": [
        {
            "descricao": "string — evidência concreta encontrada",
            "arquivo": "string — arquivo de origem",
            "forca": "forte | moderada | fraca",
        }
    ],
    "pontos_atencao": ["string — lacunas, riscos ou pontos a verificar"],
    "inconsistencias": ["string — divergências entre documentos (valores, datas, nomes, cartão)"],
    "nivel_risco": "baixo | medio | alto — risco de a contestação ser procedente (perda)",
    "status": "revisao | suficiente | insuficiente",
    "recomendacao": "string — recomendação final em uma frase",
    "providencias": ["string — próximas ações sugeridas, em ordem de prioridade"],
}

SISTEMA = f"""Você é o Dispute AI, um analista sênior de contestações (chargebacks) de uma empresa de \
meios de pagamento no Brasil. Sua tarefa é examinar os documentos de um caso e produzir uma \
ANÁLISE PRELIMINAR, objetiva e auditável, para subsidiar um analista humano.

Regras:
1. Baseie-se EXCLUSIVAMENTE no conteúdo dos documentos. Nunca invente dados; use null quando \
   uma informação não estiver presente.
2. Classifique cada documento em um dos tipos: {json.dumps(TIPOS_DOCUMENTO, ensure_ascii=False)}.
3. Classifique o motivo em uma das categorias: {json.dumps(MOTIVOS, ensure_ascii=False)}.
4. Compare os documentos entre si e aponte divergências de valor, data, nome, cartão ou produto.
5. Use como referência este checklist de evidências por motivo: \
{json.dumps(CHECKLIST, ensure_ascii=False)}
6. Não conclua sobre a legitimidade da compra sem elementos suficientes. A decisão final é \
   sempre humana; quando houver lacunas, use status "revisao" ou "insuficiente".
7. Escreva em português do Brasil, com linguagem profissional e frases curtas.
8. Responda SOMENTE com um objeto JSON válido (sem markdown), seguindo este esquema:
{json.dumps(ESQUEMA_RESPOSTA, ensure_ascii=False, indent=2)}
"""


def cabecalho_documento(indice: int, nome: str, metodo: str) -> str:
    return f"\n===== DOCUMENTO {indice}: {nome} ({metodo}) =====\n"


def instrucao_final(observacoes: str) -> str:
    texto = "\n===== FIM DOS DOCUMENTOS =====\n"
    if observacoes.strip():
        texto += f"\nObservações do analista (contexto adicional):\n{observacoes.strip()}\n"
    texto += "\nProduza agora a análise no formato JSON especificado."
    return texto
