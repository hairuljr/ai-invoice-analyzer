from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = Field(None, description="Line total as printed")


class InvoiceExtraction(BaseModel):
    """Structured output the LLM must return. Also used to validate the LLM response."""

    vendor_name: str | None = Field(None, description="Company that issued the invoice")
    invoice_number: str | None = Field(None, description="Invoice number exactly as printed")
    invoice_date: date | None = Field(None, description="Invoice date in ISO format YYYY-MM-DD")
    currency: str | None = Field(None, description="ISO 4217 code, e.g. IDR, USD")
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: float | None = Field(None, description="Total before tax, as printed")
    tax_amount: float | None = Field(None, description="Tax amount as printed, null if none")
    total_amount: float | None = Field(None, description="Grand total as a plain number, no separators")
    item_description: str | None = Field(None, description="Short description of the billed items")
    summary: str = Field(description="1-2 sentence summary of the invoice")

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
    tax_amount: float | None
    total_amount: float | None
    item_description: str | None
    summary: str
    needs_review: bool
    review_notes: list[str]
    original_filename: str
    created_at: datetime
