from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

import httpx
from pydantic import BaseModel

from backend.app.core.config import get_settings


StructuredPayload = TypeVar("StructuredPayload", bound=BaseModel)
logger = logging.getLogger("monopoly.llm")


def _validated_json_content(
    schema: type[StructuredPayload],
    content: str,
) -> StructuredPayload:
    cleaned = content.strip()
    fenced = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        return schema.model_validate_json(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Ollama response does not contain a JSON object")
        return schema.model_validate_json(cleaned[start : end + 1])


def _generate_with_ollama(
    schema: type[StructuredPayload],
    *,
    system_prompt: str,
    user_content: str,
) -> StructuredPayload:
    settings = get_settings()
    schema_json = json.dumps(
        schema.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    grounded_system_prompt = (
        f"{system_prompt}\n\n"
        "Chỉ trả về một JSON object hợp lệ, không Markdown, không văn bản ngoài JSON. "
        "JSON phải tuân thủ chính xác schema sau:\n"
        f"{schema_json}"
    )
    messages = [
        {"role": "system", "content": grounded_system_prompt},
        {"role": "user", "content": user_content},
    ]
    for attempt in range(2):
        response = httpx.post(
            f"{settings.ollama_base_url}/chat",
            headers={
                "Authorization": f"Bearer {settings.ollama_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ollama_model,
                "stream": False,
                "format": "json",
                "messages": messages,
                "options": {"temperature": 0},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama returned an empty response")
        try:
            return _validated_json_content(schema, content)
        except Exception:
            if attempt == 1:
                raise
            messages = [
                *messages,
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        "JSON trên chưa khớp schema. Hãy sửa và chỉ trả về đúng "
                        "một JSON object hợp lệ theo schema đã cung cấp."
                    ),
                },
            ]
    raise RuntimeError("Ollama JSON validation retry exhausted")


def generate_structured(
    schema: type[StructuredPayload],
    *,
    system_prompt: str,
    user_content: str,
) -> tuple[StructuredPayload | None, str]:
    """Call the configured provider without exposing optimizer-only data.

    Provider failures intentionally return a deterministic fallback signal. The
    caller owns the fallback text and every numeric fact shown to the user.
    """

    settings = get_settings()
    provider = settings.active_llm_provider
    if provider == "deterministic":
        return None, "DETERMINISTIC_FALLBACK"

    try:
        if provider == "ollama":
            parsed = _generate_with_ollama(
                schema,
                system_prompt=system_prompt,
                user_content=user_content,
            )
            return parsed, "OLLAMA_STRUCTURED_OUTPUT"

        from openai import OpenAI

        if provider == "groq":
            client = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            try:
                completion = client.chat.completions.parse(
                    model=settings.groq_model,
                    messages=messages,
                    response_format=schema,
                    temperature=0,
                )
                parsed = completion.choices[0].message.parsed
            except Exception as strict_error:
                # Groq's strict JSON-schema mode can occasionally reject an
                # otherwise valid generation. Retry once in JSON-object mode,
                # then validate locally with the same Pydantic schema.
                logger.warning(
                    "Groq strict structured output failed; retrying in JSON mode: %s",
                    type(strict_error).__name__,
                )
                schema_json = json.dumps(
                    schema.model_json_schema(),
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                retry_messages = [
                    {
                        "role": "system",
                        "content": (
                            f"{system_prompt}\n\n"
                            "Chỉ trả về một JSON object hợp lệ, không Markdown, "
                            "tuân thủ chính xác JSON Schema sau:\n"
                            f"{schema_json}"
                        ),
                    },
                    {"role": "user", "content": user_content},
                ]
                completion = client.chat.completions.create(
                    model=settings.groq_model,
                    messages=retry_messages,
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                content = completion.choices[0].message.content
                if not content:
                    raise ValueError("Groq returned an empty JSON response")
                parsed = schema.model_validate_json(content)

            return parsed, "GROQ_STRUCTURED_OUTPUT"

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            text_format=schema,
        )
        parsed = response.output_parsed
        return parsed, (
            "OPENAI_STRUCTURED_OUTPUT"
            if parsed is not None
            else "DETERMINISTIC_FALLBACK"
        )
    except Exception:
        logger.exception(
            "Structured LLM provider failed; using deterministic fallback",
            extra={"provider": provider, "model": settings.active_llm_model},
        )
        return None, "DETERMINISTIC_FALLBACK"
