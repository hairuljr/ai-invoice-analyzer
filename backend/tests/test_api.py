"""Integration test of the HTTP flow: upload -> (mocked) AI -> DB -> history.

Uses in-memory SQLite and a mocked LLM so it runs without Postgres or an API key.
TestClient is not used as a context manager, so the app's startup hook (Postgres create_all) does not run.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.db import Base, get_db
from app.llm import ExtractionError
from app.schemas import InvoiceExtraction

PDF = b"%PDF-1.4 dummy invoice"


@pytest.fixture
def client(monkeypatch):
    # StaticPool: one shared connection, so every request sees the same in-memory database.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(engine, expire_on_commit=False)

    def override_get_db():
        with TestSession() as session:
            yield session

    main.app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(
        main,
        "extract_invoice",
        lambda data, mime: InvoiceExtraction(
            vendor_name="PT Medika Sejahtera",
            invoice_number="INV-2026-00125",
            invoice_date="2026-10-01",
            total_amount=15750000,
            currency="IDR",
            item_description="Medical supplies",
            summary="Invoice untuk pembelian medical supplies senilai Rp15,75 juta.",
        ),
    )
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def upload(client, name="invoice.pdf", data=PDF):
    return client.post("/api/invoices/process", files={"file": (name, data, "application/pdf")})


def test_process_then_list(client):
    response = upload(client)
    assert response.status_code == 201
    created = response.json()
    assert created["vendor_name"] == "PT Medika Sejahtera"
    assert created["invoice_date"] == "2026-10-01"
    assert created["total_amount"] == 15750000
    assert created["original_filename"] == "invoice.pdf"

    history = client.get("/api/invoices").json()
    assert [inv["id"] for inv in history] == [created["id"]]
    assert client.get(f"/api/invoices/{created['id']}").json() == created


def test_rejects_unsupported_file(client):
    response = upload(client, name="notes.txt", data=b"hello")
    assert response.status_code == 415
    assert client.get("/api/invoices").json() == []  # nothing stored


def test_llm_failure_returns_502_and_stores_nothing(client, monkeypatch):
    def failing(data, mime):
        raise ExtractionError("AI service error: APITimeoutError")

    monkeypatch.setattr(main, "extract_invoice", failing)
    response = upload(client)
    assert response.status_code == 502
    assert "APITimeoutError" in response.json()["detail"]
    assert client.get("/api/invoices").json() == []


def test_unknown_invoice_returns_404(client):
    assert client.get("/api/invoices/999").status_code == 404


def test_same_file_reuses_stored_result_without_llm_call(client, monkeypatch):
    first = upload(client)
    assert first.status_code == 201

    def must_not_be_called(data, mime):
        raise AssertionError("LLM should not be called for a file already processed")

    monkeypatch.setattr(main, "extract_invoice", must_not_be_called)
    second = upload(client)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(client.get("/api/invoices").json()) == 1


def test_same_invoice_in_different_file_is_flagged_as_duplicate(client):
    first = upload(client).json()
    second = upload(client, name="scan.pdf", data=PDF + b" rescanned").json()
    assert first["needs_review"] is False
    assert second["needs_review"] is True
    assert f"Possible duplicate of invoice #{first['id']}" in second["review_notes"][0]


def test_wrong_total_is_stored_with_review_flag(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "extract_invoice",
        lambda data, mime: InvoiceExtraction(
            vendor_name="PT Sarana", invoice_number="SSI-1", invoice_date="2026-10-22",
            subtotal=6_300_000, tax_amount=693_000, total_amount=7_000_000, summary="s",
        ),
    )
    body = upload(client).json()
    assert body["needs_review"] is True
    assert "total is 7,000,000" in body["review_notes"][0]
    assert client.get(f"/api/invoices/{body['id']}").json()["review_notes"] == body["review_notes"]
