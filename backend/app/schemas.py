import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Must match the VARCHAR lengths in models.py / db/schema.sql, so an over-long value is cut here
# instead of failing the INSERT (a misleading 503 after the AI call was already paid for).
MAX_LENGTHS = {"vendor_name": 255, "invoice_number": 100}
CURRENCY_ALIASES = {"RP": "IDR", "RUPIAH": "IDR"}


class LineItem(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)  # NaN/Infinity is not a valid amount

    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = Field(None, description="Line total as printed")


class InvoiceExtraction(BaseModel):
    """Structured output the LLM must return. Also used to validate the LLM response."""

    model_config = ConfigDict(allow_inf_nan=False)  # NaN/Infinity is not a valid amount

    is_invoice: bool = Field(True, description="false if the document is not an invoice or bill")
    vendor_name: str | None = Field(None, description="Company that issued the invoice")
    invoice_number: str | None = Field(None, description="Invoice number exactly as printed")
    invoice_date: date | None = Field(None, description="Invoice date in ISO format YYYY-MM-DD")
    currency: str | None = Field(None, description="ISO 4217 code, e.g. IDR, USD")
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: float | None = Field(None, description="Sum of line items before discount and tax, as printed")
    discount_amount: float | None = Field(None, description="Total discount as a positive number, null if none")
    tax_amount: float | None = Field(None, description="Tax amount as printed, null if none")
    total_amount: float | None = Field(
        None, description="Grand total after discount and tax, before deducting down payments"
    )
    item_description: str | None = Field(None, description="Short description of the billed items")
    summary: str = Field(description="1-2 sentence summary of the invoice")

    @field_validator("line_items", mode="before")
    @classmethod
    def null_list_to_empty(cls, v: object) -> object:
        # Models often send null instead of [] when there are no items (e.g. a non-invoice).
        return [] if v is None else v

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: object) -> object:
        # Column is VARCHAR(3): "rupiah" -> "IDR", "usd" -> "USD", anything else unusable -> null.
        if not isinstance(v, str):
            return v
        code = v.strip().upper().rstrip(".")
        code = CURRENCY_ALIASES.get(code, code)
        return code if re.fullmatch(r"[A-Z]{3}", code) else None

    @field_validator(*MAX_LENGTHS, mode="after")
    @classmethod
    def truncate_to_column(cls, v: str | None, info) -> str | None:
        return v[: MAX_LENGTHS[info.field_name]] if v else v

    @field_validator("invoice_date", mode="before")
    @classmethod
    def invalid_date_to_none(cls, v: object) -> object:
        # A non-ISO date from the LLM becomes null instead of failing the whole extraction.
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                return None
        return v


class InvoiceOut(BaseModel):
    """API response for one stored invoice."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_name: str | None
    invoice_number: str | None
    invoice_date: date | None
    currency: str | None
    line_items: list[LineItem]
    subtotal: float | None
    discount_amount: float | None
    tax_amount: float | None
    total_amount: float | None
    item_description: str | None
    summary: str
    needs_review: bool
    review_notes: list[str]
    original_filename: str
    created_at: datetime
