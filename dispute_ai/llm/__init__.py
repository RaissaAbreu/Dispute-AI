"""Camada de abstração para provedores de LLM (Anthropic, OpenAI e Google Gemini)."""

from .base import ErroLLM, Parte, gerar_resposta

__all__ = ["ErroLLM", "Parte", "gerar_resposta"]
