# AI Invoice Analyzer

Prototype for a finance team: upload an invoice (PDF, JPG or PNG), let an AI model read it, store the
structured result in PostgreSQL, and show the result plus the history of processed invoices.

```
Browser (React)                 FastAPI                                LLM (Gemini via OpenAI-compatible proxy)
 upload form  ── POST /api/invoices/process ──> validate file
                                                same file hash seen? ─ yes ─> return stored result (200, no AI call)
                                                         │ no
                                                         └──────────────> 1 multimodal call: OCR + extraction + summary
                                                arithmetic + duplicate <── JSON (schema-validated with Pydantic)
                                                checks -> needs_review
 result card  <── 201 JSON ──────────────────── save to Postgres
 history      ── GET /api/invoices ──────────> SELECT ... ORDER BY created_at DESC
```

## What it does

- **Extracts** `vendor_name`, `invoice_number`, `invoice_date` (ISO), `currency`, `line_items`
  (description, quantity, unit price, amount), `subtotal`, `discount_amount`, `tax_amount`, `total_amount`,
  `item_description`, and a 1-2 sentence `summary` in Bahasa Indonesia. Fields the model cannot find are stored
  as `null`; it is instructed never to guess. `total_amount` is the grand total (after discount and tax), not
  the remaining balance after a down payment.
- **Rejects non-invoices.** The model also answers `is_invoice`; a letter or memo gets `422` and is not stored.
- **Verifies instead of trusting.** The LLM only reads; code checks the arithmetic (qty x unit price = amount,
  sum of lines = subtotal, subtotal - discount + tax = total), required fields, and whether the same vendor + invoice
  number was already recorded. Any problem sets `needs_review = true` with `review_notes` in Bahasa Indonesia that state the gap and the next
  action, e.g. "Total tercetak Rp 7.000.000, tetapi subtotal - diskon + pajak = Rp 6.993.000 (selisih Rp 7.000).
  Periksa dokumen asli." The
  invoice is still saved, so finance gets the data but knows to check it.
- **Does not pay twice.** A SHA-256 hash of the file is stored; uploading the identical file again returns the
  stored result (`200`) without calling the LLM.

## Project layout

```
backend/
  app/
    main.py        FastAPI app: routes, request logging, error handlers
    llm.py         the single LLM call (OpenAI SDK, custom base_url, timeout, retries)
    prompts/       extraction prompt, kept out of code
    schemas.py     Pydantic models: LLM output contract + API response
    checks.py      deterministic arithmetic / missing-field checks -> review notes
    uploads.py     file validation (extension, size, magic bytes)
    models.py      SQLAlchemy model for the invoices table
    db.py, config.py
  scripts/         make_samples.py, smoke_llm.py, evaluate.py
  tests/           unit + API integration tests (LLM mocked)
frontend/          React (Vite): upload form, result card, history table
db/schema.sql      init script for PostgreSQL (db/migrations/ upgrades an older table)
samples/           dummy invoices (fictional data, one with a deliberately wrong total), a non-invoice memo,
                   and the expected.json golden set
docs/              recorded API responses and evaluation output
```

## Setup

Prerequisites: Python 3.12+ (developed on 3.15), Bun 1.1+ (or Node 20+), PostgreSQL 14+, and an API key for an
OpenAI-compatible endpoint that serves a multimodal model (developed with Gemini through an AI proxy).

```bash
# 1. Database
createdb ai_invoice_analyzer
psql -d ai_invoice_analyzer -f db/schema.sql   # new DB: optional, the app creates the table on startup
# existing DB from an earlier version: run db/migrations/*.sql in order (startup does not ALTER tables)

# 2. Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env    # then fill in LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, DATABASE_URL

# 3. Frontend (built once, then served by FastAPI)
cd ../frontend
bun install
bun run build

# 4. Run
cd ../backend
.venv/bin/uvicorn app.main:app --port 8000
```

Open http://localhost:8000. For frontend development with hot reload, run `bun run dev` in `frontend/`
and open http://localhost:5173 (Vite proxies `/api` to port 8000).

### Environment variables (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `LLM_BASE_URL` | empty (api.openai.com) | OpenAI-compatible endpoint, e.g. an AI proxy |
| `LLM_API_KEY` | empty | API key for that endpoint. Never committed. |
| `LLM_MODEL` | `gemini-2.5-flash` | Must accept PDF and images |
| `LLM_TIMEOUT_SECONDS` | `60` | Per-request timeout; the SDK retries once on timeout/429/5xx |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/ai_invoice_analyzer` | SQLAlchemy URL |
| `MAX_UPLOAD_MB` | `10` | Upload size limit |

## Try it

UI: open http://localhost:8000, choose a file from `samples/`, click **Process invoice**. The result card
shows the extracted fields, line items and a review badge; the history table below lists all invoices (click
a row to view it). Try `samples/invoice_wrong_total.pdf` to see an invoice flagged **Needs review**, and upload
the same file twice to see the stored result reused. `samples/not_an_invoice_memo.pdf` is rejected with `422`.

API:

```bash
curl -F "file=@samples/invoice_medika.pdf" http://localhost:8000/api/invoices/process
curl http://localhost:8000/api/invoices
curl http://localhost:8000/api/invoices/1
curl http://localhost:8000/health
```

Interactive API docs: http://localhost:8000/docs. Real recorded responses: [docs/api_examples.md](docs/api_examples.md).

Screenshots (taken during development; review notes were later translated to Bahasa Indonesia and empty
amount rows are now hidden): [USD invoice with line items and history](docs/screenshots/ui-usd-invoice-result.png),
[wrong total flagged for review](docs/screenshots/ui-wrong-total-needs-review.png).

| Endpoint | Success | Errors |
|---|---|---|
| `POST /api/invoices/process` (multipart `file`) | `201` + stored invoice; `200` if this exact file was processed before | `400` empty, `413` too large, `415` wrong type or content does not match extension, `422` not an invoice, `502` AI failed or returned invalid output, `503` database unavailable |
| `GET /api/invoices?limit=50` | `200` list, newest first | |
| `GET /api/invoices/{id}` | `200` | `404` |
| `GET /health` | `200` (checks the database) | `503` |

## Database

One table, `invoices` ([db/schema.sql](db/schema.sql)): extracted fields (nullable), `line_items` and
`review_notes` (JSONB), `needs_review`, `summary`, `original_filename`, `file_sha256` (indexed, for reuse), and
`created_at` (indexed, for history ordering). Amounts are `NUMERIC(18,2)` to avoid floating-point errors on
money, and `invoice_date` is a real `DATE`. A database created from an earlier version is upgraded in place with
the scripts in `db/migrations/`, in order (idempotent, non-destructive).

## Tests and evaluation

```bash
cd backend
.venv/bin/python -m pytest              # 50 tests, no API key or Postgres needed (LLM mocked, SQLite in memory)
.venv/bin/python -m scripts.evaluate     # real LLM vs samples/expected.json golden set
```

Latest evaluation ([docs/evaluation.txt](docs/evaluation.txt)): 4/4 invoices correct on all seven structured
fields, and the review flag is right on all 4 (the wrong-total invoice is flagged, the clean ones are not).
About 9 seconds per invoice.

Edge cases ([docs/edge_cases.md](docs/edge_cases.md)): multi-page invoice with 60 lines, discount and down
payment; USD with decimals; Indonesian decimal comma; missing fields; a non-invoice; skewed scan; low-res photo;
and five invalid uploads. All handled without a crash; see the report for each result.

## Key decisions

See [DECISIONS.md](DECISIONS.md). In short: one multimodal LLM call instead of OCR + LLM, a Pydantic schema
as the contract with the model, arithmetic verified in code rather than by the model, magic-byte file
validation, Numeric money, and a small React app served by FastAPI.

## Limitations

- Synchronous processing: the request waits for the LLM (usually 7-10 s, occasionally much longer through the proxy).
- Evaluation covers 4 golden invoices plus 13 edge cases, all generated. Real-world scans and handwriting are untested.
- The checks catch inconsistent numbers, not a consistently misread invoice (e.g. a wrong vendor name).
- Uploaded files are not stored, only the extracted data and the file hash.
- No auth, no edit/delete or "mark as reviewed", no pagination beyond `limit`.
- Two simultaneous uploads of the same new file can both call the AI and create two rows (the hash index is not
  UNIQUE). The UI disables the button while processing; a UNIQUE constraint is the production fix.
- No Docker setup yet (Docker was not available on the development machine, so it was not added untested).
- Privacy: the full document is sent to an external LLM provider. Invoices to a hospital can contain personal
  data. This prototype does not claim compliance with UU PDP (Law 27/2022). See next steps.

## Next steps

- Async processing (queue + worker) with a status field, so uploads return immediately.
- Store originals in object storage (GCS/S3) with a retention policy; link them to the record.
- A review workflow: mark flagged invoices as reviewed/corrected, with an audit trail.
- Privacy: PII redaction before the LLM call, a provider with a data processing agreement and in-region
  processing, audit logging, access control.
- Alembic migrations, Docker Compose + CI, and a larger golden set with anonymised real scans.
