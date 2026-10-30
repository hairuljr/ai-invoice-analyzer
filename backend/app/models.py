from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, Numeric, String, Text, false, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# JSONB on Postgres, plain JSON elsewhere (SQLite in tests).
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Invoice(Base):
    """Keep in sync with db/schema.sql."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Extracted fields are nullable: the LLM returns null rather than guessing.
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str | None] = mapped_column(String(3))
    line_items: Mapped[list[dict]] = mapped_column(JsonType, default=list)
    # Numeric, not float: money must not suffer binary rounding errors.
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    item_description: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(Boolean, server_default=false())
    review_notes: Mapped[list[str]] = mapped_column(JsonType, default=list)
    original_filename: Mapped[str] = mapped_column(String(255))
    # Same file uploaded again -> reuse the stored result instead of paying for another LLM call.
    file_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
