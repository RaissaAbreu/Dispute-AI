"""Interface comum para chamadas aos provedores de LLM.

Cada provedor recebe a mesma lista de "partes" (texto e imagens) e devolve o texto
gerado. A importação dos SDKs é feita sob demanda, para que o sistema funcione
mesmo que apenas um dos pacotes esteja instalado.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass


class ErroLLM(RuntimeError):
    """Erro amigável ao usuário durante a chamada ao provedor de LLM."""


@dataclass
class Parte:
    tipo: str  # "texto" | "imagem"
    texto: str = ""
    mime: str = ""
    dados: bytes = b""

    @property
    def base64(self) -> str:
        return base64.standard_b64encode(self.dados).decode("ascii")


MAX_TOKENS_RESPOSTA = 8000


def _anthropic(chave: str, modelo: str, sistema: str, partes: list[Parte]) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise ErroLLM("Pacote 'anthropic' não instalado. Execute: pip install anthropic") from exc

    conteudo = []
    for p in partes:
        if p.tipo == "imagem":
            conteudo.append(
                {"type": "image", "source": {"type": "base64", "media_type": p.mime, "data": p.base64}}
            )
        else:
            conteudo.append({"type": "text", "text": p.texto})

    cliente = anthropic.Anthropic(api_key=chave)
    try:
        resp = cliente.messages.create(
            model=modelo,
            max_tokens=MAX_TOKENS_RESPOSTA,
            system=sistema,
            messages=[{"role": "user", "content": conteudo}],
        )
    except anthropic.AuthenticationError as exc:
        raise ErroLLM("Chave da Anthropic inválida.") from exc
    except anthropic.NotFoundError as exc:
        raise ErroLLM(f"Modelo '{modelo}' não encontrado na Anthropic.") from exc
    except anthropic.APIError as exc:
        raise ErroLLM(f"Erro na API da Anthropic: {exc}") from exc
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _openai(chave: str, modelo: str, sistema: str, partes: list[Parte]) -> str:
    try:
        import openai
    except ImportError as exc:
        raise ErroLLM("Pacote 'openai' não instalado. Execute: pip install openai") from exc

    conteudo = []
    for p in partes:
        if p.tipo == "imagem":
            conteudo.append(
                {"type": "image_url", "image_url": {"url": f"data:{p.mime};base64,{p.base64}"}}
            )
        else:
            conteudo.append({"type": "text", "text": p.texto})

    cliente = openai.OpenAI(api_key=chave)
    try:
        resp = cliente.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": conteudo},
            ],
            response_format={"type": "json_object"},
        )
    except openai.AuthenticationError as exc:
        raise ErroLLM("Chave da OpenAI inválida.") from exc
    except openai.NotFoundError as exc:
        raise ErroLLM(f"Modelo '{modelo}' não encontrado na OpenAI.") from exc
    except openai.APIError as exc:
        raise ErroLLM(f"Erro na API da OpenAI: {exc}") from exc
    return resp.choices[0].message.content or ""


def _gemini(chave: str, modelo: str, sistema: str, partes: list[Parte]) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ErroLLM("Pacote 'google-genai' não instalado. Execute: pip install google-genai") from exc

    conteudo = []
    for p in partes:
        if p.tipo == "imagem":
            conteudo.append(types.Part.from_bytes(data=p.dados, mime_type=p.mime))
        else:
            conteudo.append(types.Part.from_text(text=p.texto))

    cliente = genai.Client(api_key=chave)
    try:
        resp = cliente.models.generate_content(
            model=modelo,
            contents=conteudo,
            config=types.GenerateContentConfig(
                system_instruction=sistema,
                response_mime_type="application/json",
                max_output_tokens=MAX_TOKENS_RESPOSTA,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - o SDK usa várias classes de erro
        msg = str(exc)
        if "API key" in msg or "401" in msg or "403" in msg:
            raise ErroLLM("Chave do Google Gemini inválida.") from exc
        raise ErroLLM(f"Erro na API do Gemini: {msg}") from exc
    return resp.text or ""


_PROVEDORES = {"anthropic": _anthropic, "openai": _openai, "gemini": _gemini}


def gerar_resposta(provedor: str, chave: str, modelo: str, sistema: str, partes: list[Parte]) -> str:
    """Envia o prompt ao provedor escolhido e devolve o texto da resposta."""
    if provedor not in _PROVEDORES:
        raise ErroLLM(f"Provedor desconhecido: {provedor}")
    if not chave:
        raise ErroLLM("Chave de API não informada para o provedor selecionado.")
    return _PROVEDORES[provedor](chave, modelo, sistema, partes)
