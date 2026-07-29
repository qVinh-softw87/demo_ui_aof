from __future__ import annotations

import json
import logging
from typing import TypeVar

from pydantic import BaseModel

from backend.app.core.config import get_settings


StructuredPayload = TypeVar("StructuredPayload", bound=BaseModel)
logger = logging.getLogger("monopoly.llm")


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
