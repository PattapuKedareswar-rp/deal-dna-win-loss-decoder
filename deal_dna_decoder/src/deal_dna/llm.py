"""OpenAI wrapper with a safe offline fallback.

When a key is configured, `structured_json` asks the model to return JSON that validates
against a pydantic model. In offline mode callers use their own deterministic logic instead.
The key is read from the environment only.
"""
from __future__ import annotations

import json
from typing import Type, TypeVar

from pydantic import BaseModel

from . import config

T = TypeVar("T", bound=BaseModel)


def is_offline() -> bool:
    return config.is_offline()


def structured_json(system: str, user: str, model_cls: Type[T]) -> T:
    """Call OpenAI and parse the reply into `model_cls`. Raises in offline mode."""
    if is_offline():
        raise RuntimeError("structured_json called in offline mode; use the deterministic path.")

    from openai import OpenAI  # imported lazily so offline mode needs no SDK install

    client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
    schema_hint = json.dumps(model_cls.model_json_schema())
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system + "\n\nReturn ONLY JSON matching this schema:\n" + schema_hint},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    payload = resp.choices[0].message.content or "{}"
    return model_cls.model_validate_json(payload)
