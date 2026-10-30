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


def test_retries_once_on_invalid_output(monkeypatch):
    replies = iter(["not json", VALID])
    calls = []

    def create(**kwargs):
        calls.append(1)
        content = next(replies)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "get_client", lambda: client)
    assert extract_invoice(b"%PDF-", "application/pdf").vendor_name == "PT Medika"
    assert len(calls) == 2


def test_null_line_items_become_empty_list():
    # Real model output for a non-invoice document.
    assert InvoiceExtraction(is_invoice=False, line_items=None, summary="Bukan invoice.").line_items == []


def test_empty_choices_raise_extraction_error(monkeypatch):
    response = SimpleNamespace(choices=[])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
    monkeypatch.setattr(llm, "get_client", lambda: client)
    with pytest.raises(ExtractionError):
        extract_invoice(b"%PDF-", "application/pdf")


def test_non_openai_exception_becomes_extraction_error(monkeypatch):
    def create(**kwargs):
        raise ValueError("proxy sent something unexpected")

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "get_client", lambda: client)
    with pytest.raises(ExtractionError, match="ValueError"):
        extract_invoice(b"%PDF-", "application/pdf")


@pytest.mark.parametrize(
    "raw, expected",
    [("IDR", "IDR"), ("usd", "USD"), ("Rp.", "IDR"), ("RUPIAH", "IDR"), ("US Dollar", None), ("", None), (None, None)],
)
def test_currency_is_normalized_to_iso_code_or_null(raw, expected):
    assert InvoiceExtraction(currency=raw, summary="s").currency == expected


def test_long_strings_are_cut_to_column_length():
    ext = InvoiceExtraction(vendor_name="V" * 300, invoice_number="N" * 150, summary="s")
    assert len(ext.vendor_name) == 255 and len(ext.invoice_number) == 100


def test_nan_amount_is_rejected():
    with pytest.raises(ValueError):
        InvoiceExtraction.model_validate_json('{"total_amount": NaN, "summary": "s"}')
