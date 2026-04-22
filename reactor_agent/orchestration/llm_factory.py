"""
Multi-provider LLM factory.

Reads LLM_PROVIDER and LLM_MODEL from the environment, lazy-imports the
required SDK, and exposes a single function:

    get_llm_response(prompt: str, system: str = "") -> str

Supported providers (set LLM_PROVIDER):
  groq       — default model: llama-3.1-70b-versatile
  openai     — default model: gpt-4o-mini
  anthropic  — default model: claude-3-haiku-20240307
  ollama     — default model: llama3.2
"""

import os
from typing import Optional

# Default models per provider
_DEFAULTS = {
    "groq": "llama-3.1-70b-versatile",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-haiku-20240307",
    "ollama": "llama3.2",
}


def get_llm_response(
    prompt: str,
    system: str = "You are a helpful assistant.",
    provider=None,
    model=None,
) -> str:
    """
    Call the configured LLM and return the response string.

    Parameters
    ----------
    prompt : str
        User message / query.
    system : str
        System message framing the LLM's role.
    provider : str, optional
        Override LLM_PROVIDER env var.
    model : str, optional
        Override LLM_MODEL env var.

    Returns
    -------
    str  — raw text response from the LLM.
    """
    _provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower().strip()
    _model = model or os.getenv("LLM_MODEL", "") or _DEFAULTS.get(_provider, "")

    if _provider == "groq":
        return _call_groq(prompt, system, _model)
    elif _provider == "openai":
        return _call_openai(prompt, system, _model)
    elif _provider == "anthropic":
        return _call_anthropic(prompt, system, _model)
    elif _provider == "ollama":
        return _call_ollama(prompt, system, _model)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{_provider}'. "
            "Choose: groq, openai, anthropic, ollama"
        )


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _call_groq(prompt: str, system: str, model: str) -> str:
    try:
        from groq import Groq
    except ImportError as exc:
        raise ImportError("Install groq: pip install groq") from exc

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def _call_openai(prompt: str, system: str, model: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError("Install openai: pip install openai") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def _call_anthropic(prompt: str, system: str, model: str) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise ImportError("Install anthropic: pip install anthropic") from exc

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_ollama(prompt: str, system: str, model: str) -> str:
    try:
        import ollama
    except ImportError as exc:
        raise ImportError("Install ollama: pip install ollama") from exc

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response["message"]["content"]
