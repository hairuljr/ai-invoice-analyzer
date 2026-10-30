from datetime import date
from types import SimpleNamespace

import pytest

from app import llm
from app.llm import ExtractionError, extract_invoice
from app.schemas import InvoiceExtraction


def fake_client(content: str):
    """Mimics openai's client.chat.completions.create(...) returning `content`."""
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    completions = SimpleNamespace(create=lambda **kwargs: response)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


VALID = (
    '{"vendor_name": "PT Medika", "invoice_number": "INV-1", "invoice_date": "2026-10-01",'
    ' "total_amount": 15750000, "currency": "IDR", "item_description": "Medical supplies",'
    ' "summary": "Invoice medical supplies."}'
)


def test_parses_valid_json(monkeypatch):
    monkeypatch.setattr(llm, "get_client", lambda: fake_client(VALID))
    result = extract_invoice(b"%PDF-", "application/pdf")
    assert result.vendor_name == "PT Medika"
    assert result.invoice_date == date(2026, 10, 1)
    assert result.total_amount == 15750000


def test_strips_markdown_code_fence(monkeypatch):
    monkeypatch.setattr(llm, "get_client", lambda: fake_client(f"```json\n{VALID}\n```"))
    assert extract_invoice(b"%PDF-", "application/pdf").invoice_number == "INV-1"


@pytest.mark.parametrize("content", ["not json", '{"vendor_name": "x"}', ""])  # missing summary is invalid
def test_invalid_output_raises_extraction_error(monkeypatch, content):
    monkeypatch.setattr(llm, "get_client", lambda: fake_client(content))
    with pytest.raises(ExtractionError):
        extract_invoice(b"%PDF-", "application/pdf")


@pytest.mark.parametrize("raw", ["01/10/2026", "1 Oktober 2026", "not a date"])
def test_non_iso_date_becomes_null(raw):
    assert InvoiceExtraction(invoice_date=raw, summary="s").invoice_date is None
