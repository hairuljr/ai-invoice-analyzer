# AI Invoice Analyzer

Prototype for a finance team: upload an invoice (PDF, JPG or PNG), let an AI model read it, store the
structured result in PostgreSQL, and show the result plus the history of processed invoices.

```
Browser (React)                 FastAPI                          LLM (Gemini via OpenAI-compatible proxy)
 upload form  ── POST /api/invoices/process ──> validate file ──> 1 multimodal call: OCR + extraction + summary
 result card  <── 201 JSON ──────────────────── save to Postgres <── JSON (schema-validated with Pydantic)
 history      ── GET /api/invoices ──────────> SELECT ... ORDER BY created_at DESC
```

## What it extracts

`vendor_name`, `invoice_number`, `invoice_date` (ISO), `total_amount` (number), `currency`, `item_description`,
and a 1-2 sentence `summary` in Bahasa Indonesia. Fields the model cannot find are stored as `null`; it is
instructed never to guess.

## Project layout

```
backend/
  app/
    main.py        FastAPI app: routes, request logging, error handlers
    llm.py         the single LLM call (OpenAI SDK, custom base_url, timeout, retry)
    prompts/       extraction prompt, kept out of code
    schemas.py     Pydantic models: LLM output contract + API response
    uploads.py     file validation (extension, size, magic bytes)
    models.py      SQLAlchemy model for the invoices table
    db.py, config.py
  scripts/         make_samples.py, smoke_llm.py, evaluate.py
  tests/           unit + API integration tests (LLM mocked)
frontend/          React (Vite): upload form, result card, history table
db/schema.sql      init script for PostgreSQL
samples/           dummy invoices (fictional data) + expected.json golden set
docs/              recorded API responses and evaluation output
```

## Setup

Prerequisites: Python 3.12+ (developed on 3.15), Node 20+, PostgreSQL 14+, and an API key for an
OpenAI-compatible endpoint that serves a multimodal model (developed with Gemini through an AI proxy).

```bash
# 1. Database
createdb ai_invoice_analyzer
psql -d ai_invoice_analyzer -f db/schema.sql   # optional: the app also creates the table on startup

# 2. Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env    # then fill in LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, DATABASE_URL

# 3. Frontend (built once, then served by FastAPI)
cd ../frontend
npm install
npm run build

# 4. Run
cd ../backend
.venv/bin/uvicorn app.main:app --port 8000
```

Open http://localhost:8000. For frontend development with hot reload, run `npm run dev` in `frontend/`
and open http://localhost:5173 (Vite proxies `/api` to port 8000).

### Environment variables (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `LLM_BASE_URL` | empty (api.openai.com) | OpenAI-compatible endpoint, e.g. an AI proxy |
| `LLM_API_KEY` | empty | API key for that endpoint. Never committed. |
| `LLM_MODEL` | `gemini-2.5-flash` | Must accept PDF and images |
| `LLM_TIMEOUT_SECONDS` | `90` | Per-request timeout; the SDK retries once on timeout/429/5xx |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/ai_invoice_analyzer` | SQLAlchemy URL |
| `MAX_UPLOAD_MB` | `10` | Upload size limit |

## Try it

UI: open http://localhost:8000, choose a file from `samples/`, click **Process invoice**. The result card
shows the extracted fields; the history table below lists all invoices (click a row to view it).

API:

```bash
curl -F "file=@samples/invoice_medika.pdf" http://localhost:8000/api/invoices/process
curl http://localhost:8000/api/invoices
curl http://localhost:8000/api/invoices/1
curl http://localhost:8000/health
```

Interactive API docs: http://localhost:8000/docs. Real recorded responses: [docs/api_examples.md](docs/api_examples.md).

| Endpoint | Success | Errors |
|---|---|---|
| `POST /api/invoices/process` (multipart `file`) | `201` + stored invoice | `400` empty, `413` too large, `415` wrong type or content does not match extension, `502` AI failed or returned invalid output, `503` database unavailable |
| `GET /api/invoices?limit=50` | `200` list, newest first | |
| `GET /api/invoices/{id}` | `200` | `404` |
| `GET /health` | `200` (checks the database) | `503` |

## Database

One table, `invoices` ([db/schema.sql](db/schema.sql)): extracted fields (nullable), `summary`,
`original_filename`, `created_at` (indexed, for history ordering). `total_amount` is `NUMERIC(18,2)` to avoid
floating-point errors on money, and `invoice_date` is a real `DATE`.

## Tests and evaluation

```bash
cd backend
.venv/bin/python -m pytest              # 21 tests, no API key or Postgres needed (LLM mocked, SQLite in memory)
.venv/bin/python -m scripts.evaluate     # real LLM vs samples/expected.json golden set
```

Latest evaluation ([docs/evaluation.txt](docs/evaluation.txt)): 3/3 invoices correct on all five structured
fields, about 7 seconds per invoice.

## Key decisions

See [DECISIONS.md](DECISIONS.md). In short: one multimodal LLM call instead of OCR + LLM, a Pydantic schema
as the contract with the model, magic-byte file validation, Numeric money, and a small React app served by
FastAPI.

## Limitations

- Synchronous processing: the request waits for the LLM (usually about 7 s, occasionally much longer through the proxy).
- Evaluation covers 3 clean, generated invoices only. Real scans (skewed, handwritten, multi-page) are untested.
- Uploaded files are not stored, only the extracted data.
- No auth, no edit/delete, no pagination beyond `limit`, no duplicate-invoice detection.
- No Docker setup yet (Docker was not available on the development machine, so it was not added untested).
- Privacy: the full document is sent to an external LLM provider. Invoices to a hospital can contain personal
  data. This prototype does not claim compliance with UU PDP (Law 27/2022). See next steps.

## Next steps

- Async processing (queue + worker) with a status field, so uploads return immediately.
- Store originals in object storage (GCS/S3) with a retention policy; link them to the record.
- Confidence and arithmetic checks (line items x qty = subtotal; subtotal + tax = total), flag for manual review.
- Privacy: PII redaction before the LLM call, a provider with a data processing agreement and in-region
  processing, audit logging, access control.
- Duplicate detection on (vendor_name, invoice_number); Alembic migrations; Docker Compose; larger golden set.
