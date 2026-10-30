from datetime import date

from pydantic import BaseModel, Field, field_validator


class InvoiceExtraction(BaseModel):
    """Structured output the LLM must return. Also used to validate the LLM response."""

    vendor_name: str | None = Field(None, description="Company that issued the invoice")
    invoice_number: str | None = Field(None, description="Invoice number exactly as printed")
    invoice_date: str | None = Field(None, description="Invoice date in ISO format YYYY-MM-DD")
    total_amount: float | None = Field(None, description="Grand total as a plain number, no separators")
    currency: str | None = Field(None, description="ISO 4217 code, e.g. IDR, USD")
    item_description: str | None = Field(None, description="Short description of the billed items")
    summary: str = Field(description="1-2 sentence summary of the invoice")

    @field_validator("invoice_date")
    @classmethod
    def date_must_be_iso(cls, v: str | None) -> str | None:
        # A non-ISO date from the LLM becomes null instead of being stored as garbage.
        if v is None:
            return None
        try:
            return date.fromisoformat(v).isoformat()
        except ValueError:
            return None
