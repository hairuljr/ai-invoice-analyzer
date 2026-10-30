import hashlib
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import models
from .checks import review_notes
from .config import settings
from .db import Base, engine, get_db
from .llm import ExtractionError, extract_invoice
from .schemas import InvoiceOut
from .uploads import UploadError, validate_upload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("invoice_analyzer")

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent: creates the invoices table if it does not exist yet (same DDL as db/schema.sql).
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="AI Invoice Analyzer", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    logger.info(
        "%s %s -> %d (%.0f ms)",
        request.method, request.url.path, response.status_code, (time.perf_counter() - start) * 1000,
    )
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error on %s", request.url.path)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable, please try again."})


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


# Plain `def` (not async): FastAPI runs it in a threadpool, so the blocking LLM call
# does not freeze the event loop for other requests.
@app.post(
    "/api/invoices/process",
    response_model=InvoiceOut,
    status_code=201,
    responses={200: {"description": "This exact file was processed before; the stored result is returned"}},
)
def process_invoice(file: UploadFile, response: Response, db: Session = Depends(get_db)):
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)  # read one byte past the limit to detect oversize files
    filename = file.filename or ""
    try:
        mime = validate_upload(filename, data, max_bytes)
    except UploadError as e:
        raise HTTPException(e.status_code, e.message)

    file_hash = hashlib.sha256(data).hexdigest()
    cached = db.scalars(select(models.Invoice).where(models.Invoice.file_sha256 == file_hash).limit(1)).first()
    if cached:
        logger.info("Same file as invoice id=%d, skipping LLM call", cached.id)
        response.status_code = 200
        return cached

    try:
        extracted = extract_invoice(data, mime)
    except ExtractionError as e:
        raise HTTPException(502, f"Could not extract invoice data: {e}")

    # Not stored: a non-invoice in the invoices table would be junk data in finance's history.
    if not extracted.is_invoice:
        raise HTTPException(422, f"This document does not look like an invoice. AI says: {extracted.summary}")

    notes = review_notes(extracted)
    duplicate = find_same_invoice(db, extracted.vendor_name, extracted.invoice_number)
    if duplicate:
        notes.append(f"Possible duplicate of invoice #{duplicate.id} (same vendor and invoice number).")

    invoice = models.Invoice(
        **extracted.model_dump(exclude={"is_invoice"}),
        needs_review=bool(notes),
        review_notes=notes,
        original_filename=filename,
        file_sha256=file_hash,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    logger.info("Stored invoice id=%d from %s (needs_review=%s)", invoice.id, filename, invoice.needs_review)
    return invoice


def find_same_invoice(db: Session, vendor_name: str | None, invoice_number: str | None) -> models.Invoice | None:
    if not vendor_name or not invoice_number:
        return None
    stmt = select(models.Invoice).where(
        func.lower(models.Invoice.vendor_name) == vendor_name.lower(),
        models.Invoice.invoice_number == invoice_number,
    )
    return db.scalars(stmt.limit(1)).first()


@app.get("/api/invoices", response_model=list[InvoiceOut])
def list_invoices(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(models.Invoice).order_by(models.Invoice.created_at.desc(), models.Invoice.id.desc())
    return db.scalars(stmt.limit(limit)).all()


@app.get("/api/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.get(models.Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    return invoice


# Serve the built React app (bun run build) from the same origin, if it exists.
# Mounted last so /api routes take precedence.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
