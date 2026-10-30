from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Invoice(Base):
    """Keep in sync with db/schema.sql."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Extracted fields are nullable: the LLM returns null rather than guessing.
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    # Numeric, not float: money must not suffer binary rounding errors.
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    item_description: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
