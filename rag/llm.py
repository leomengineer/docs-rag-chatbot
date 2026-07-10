"""Thin LLM dispatch — swap providers with LLM_PROVIDER env var."""

import os

from dotenv import load_dotenv

load_dotenv()


def call_llm(system, user):
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        return _openai(system, user)
    if provider == "anthropic":
        return _anthropic(system, user)
    raise ValueError(f"unknown LLM_PROVIDER: {provider}")


def _openai(system, user):
    from openai import OpenAI

    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def _anthropic(system, user):
    from anthropic import Anthropic

    client = Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0.2,
    )
    return resp.content[0].text.strip()
