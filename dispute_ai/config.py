"""Configurações centrais do Dispute AI (provedores, modelos e caminhos)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ_PROJETO / ".env")

CAMINHO_DB = Path(os.getenv("DISPUTE_AI_DB", RAIZ_PROJETO / "data" / "dispute_ai.db"))
if not CAMINHO_DB.is_absolute():
    CAMINHO_DB = RAIZ_PROJETO / CAMINHO_DB

PASTA_EXEMPLOS = RAIZ_PROJETO / "exemplos"

# Extensões aceitas no upload e seus tipos MIME.
TIPOS_ACEITOS: dict[str, str] = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "eml": "message/rfc822",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}

# Limite de caracteres de texto por documento enviado ao LLM (controle de custo).
MAX_CARACTERES_POR_DOCUMENTO = 12_000
# Páginas de PDF com menos caracteres que isso são tratadas como digitalizadas (enviadas como imagem).
MIN_CARACTERES_PAGINA_TEXTO = 40
# Máximo de páginas digitalizadas convertidas em imagem por PDF.
MAX_PAGINAS_IMAGEM_POR_PDF = 4


@dataclass(frozen=True)
class Provedor:
    chave: str
    nome: str
    variavel_ambiente: str | None
    modelos: list[str] = field(default_factory=list)
    modelo_padrao: str = ""


PROVEDORES: dict[str, Provedor] = {
    "anthropic": Provedor(
        chave="anthropic",
        nome="Anthropic (Claude)",
        variavel_ambiente="ANTHROPIC_API_KEY",
        modelos=["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"],
        modelo_padrao="claude-sonnet-5-5",
    ),
    "openai": Provedor(
        chave="openai",
        nome="OpenAI (GPT)",
        variavel_ambiente="OPENAI_API_KEY",
        modelos=["gpt-4.1", "gpt-4.1-mini", "gpt-4o"],
        modelo_padrao="gpt-4.1",
    ),
    "gemini": Provedor(
        chave="gemini",
        nome="Google Gemini",
        variavel_ambiente="GEMINI_API_KEY",
        modelos=["gemini-2.5-flash", "gemini-2.5-pro"],
        modelo_padrao="gemini-2.5-flash",
    ),
    "demo": Provedor(
        chave="demo",
        nome="Modo demonstração (sem API)",
        variavel_ambiente=None,
        modelos=["regras-v1"],
        modelo_padrao="regras-v1",
    ),
}

PROVEDOR_PADRAO = os.getenv("DISPUTE_AI_PROVEDOR_PADRAO", "demo")
if PROVEDOR_PADRAO not in PROVEDORES:
    PROVEDOR_PADRAO = "demo"


def chave_api_ambiente(provedor: str) -> str:
    """Retorna a chave de API configurada no ambiente/.env para o provedor (ou string vazia)."""
    p = PROVEDORES.get(provedor)
    if not p or not p.variavel_ambiente:
        return ""
    return os.getenv(p.variavel_ambiente, "").strip()
