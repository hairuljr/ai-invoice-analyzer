# Decisions

| Decision | Why | Alternative considered |
|---|---|---|
| One multimodal LLM call does OCR, extraction and summary | Reads layout and tables directly, one network round trip, less code to maintain | Tesseract/PaddleOCR then LLM on text: more control, can run locally, but loses layout and adds a pipeline |
| Gemini through an OpenAI-compatible proxy, `openai` SDK with `base_url` | The proxy speaks the OpenAI protocol; swapping model or provider is a config change | `google-genai` SDK: native, but would bypass the proxy |
| PDFs sent as `image_url` data URLs | The proxy dropped the `file` content part (model saw no document); `data:application/pdf` is forwarded to Gemini | Render PDF pages to PNG with pypdfium2: works everywhere, but an extra dependency |
| Pydantic model is both the `response_format` JSON schema and the validator | One contract; invalid output becomes a 502 instead of bad data in the DB | Free-form JSON plus manual checks |
| Missing fields are `null`; non-ISO dates become `null` | Never store invented values; a person can fill gaps | Reject the whole invoice |
| PostgreSQL with SQLAlchemy 2.0 | Real SQL DB as in production; ORM keeps tests portable (SQLite in tests) | SQLite: simpler, but not what a hospital would run |
| `NUMERIC(18,2)` for amounts, `DATE` for dates | Money must not suffer float rounding; dates sortable and typed | `FLOAT`/`TEXT` |
| `create_all` on startup plus `db/schema.sql` | Runs from a clean clone, while reviewers still get a plain SQL init script | Alembic migrations: right for production, overkill for one table |
| Validate extension, size and magic bytes | The client's Content-Type header can lie; magic bytes catch renamed files | Trust Content-Type |
| Sync `def` endpoint | FastAPI runs it in a threadpool, so the blocking LLM call does not block the event loop | `async` + async client: better at scale, more to explain |
| React (Vite) single page, built and served by FastAPI | The brief asks for React; one origin, no CORS; one component file is easy to follow | Next.js: unnecessary for one page |
| LLM mocked in tests, real LLM only in `scripts/evaluate.py` | Tests are fast, free and deterministic; evaluation measures real accuracy separately | Calling the real model in tests |
