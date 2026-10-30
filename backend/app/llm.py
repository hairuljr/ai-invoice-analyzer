"""Thin wrapper around one multimodal LLM call: document bytes in, validated InvoiceExtraction out.

The AI proxy is OpenAI-compatible, so we use the openai SDK with a custom base_url.
OCR, field extraction and summary all happen in this single call.
"""

import base64
import logging
from functools import cache
from pathlib import Path

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from .config import settings
from .schemas import InvoiceExtraction

logger = logging.getLogger(__name__)

PROMPT = (Path(__file__).parent / "prompts" / "extract_invoice.txt").read_text()


class ExtractionError(Exception):
    """The LLM call failed or returned output we cannot trust."""


@cache
def get_client() -> OpenAI:
    # Created on first use (not at import) so tests can run without an API key.
    return OpenAI(
        base_url=settings.llm_base_url or None,
        api_key=settings.llm_api_key,
        timeout=settings.llm_timeout_seconds,
        max_retries=1,  # SDK retries once on timeouts, 429 and 5xx
    )


def _file_part(data: bytes, mime: str) -> dict:
    # PDFs also go through image_url: our proxy drops the "file" content part
    # (model saw no document) but forwards a data:application/pdf URL to Gemini.
    data_url = f"data:{mime};base64,{base64.b64encode(data).decode()}"
    return {"type": "image_url", "image_url": {"url": data_url}}


def _strip_code_fence(text: str) -> str:
    # A proxy may ignore response_format, and some models then wrap JSON in ```json ... ```.
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    return text.strip()


def extract_invoice(data: bytes, mime: str) -> InvoiceExtraction:
    messages = [
        {"role": "system", "content": PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract the data from this invoice."},
                _file_part(data, mime),
            ],
        },
    ]
    try:
        resp = get_client().chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "invoice_extraction",
                    "schema": InvoiceExtraction.model_json_schema(),
                },
            },
        )
    except OpenAIError as e:
        logger.error("LLM request failed: %s", e)
        raise ExtractionError(f"AI service error: {e.__class__.__name__}") from e

    content = resp.choices[0].message.content or ""
    try:
        return InvoiceExtraction.model_validate_json(_strip_code_fence(content))
    except ValidationError as e:
        logger.error("LLM returned invalid JSON: %.500s", content)
        raise ExtractionError("AI returned an invalid response") from e
