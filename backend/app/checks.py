"""Deterministic checks on the LLM output. Code verifies the arithmetic; the LLM only reads.

Anything suspicious becomes a review note, and an invoice with notes is flagged for manual review
instead of being rejected: finance still gets the data, but knows not to trust it blindly.
"""

from .schemas import InvoiceExtraction

REQUIRED_FIELDS = ["vendor_name", "invoice_number", "invoice_date", "total_amount"]
# Absolute, not relative: 0.1% of Rp7,000,000 would hide a Rp7,000 error. 1 unit covers tax rounding.
TOLERANCE = 1.0


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE


def _fmt(n: float) -> str:
    return f"{n:,.2f}".rstrip("0").rstrip(".")


def review_notes(ext: InvoiceExtraction) -> list[str]:
    notes = []

    missing = [field for field in REQUIRED_FIELDS if getattr(ext, field) is None]
    if missing:
        notes.append(f"Missing fields: {', '.join(missing)}.")

    for item in ext.line_items:
        if None not in (item.quantity, item.unit_price, item.amount):
            expected = item.quantity * item.unit_price
            if not _close(expected, item.amount):
                notes.append(
                    f"Line '{item.description}': {_fmt(item.quantity)} x {_fmt(item.unit_price)}"
                    f" = {_fmt(expected)}, but the invoice says {_fmt(item.amount)}."
                )

    amounts = [item.amount for item in ext.line_items]
    if amounts and None not in amounts and ext.subtotal is not None:
        if not _close(sum(amounts), ext.subtotal):
            notes.append(f"Line items add up to {_fmt(sum(amounts))}, but the subtotal is {_fmt(ext.subtotal)}.")

    if ext.subtotal is not None and ext.total_amount is not None:
        expected_total = ext.subtotal - (ext.discount_amount or 0) + (ext.tax_amount or 0)
        if not _close(expected_total, ext.total_amount):
            notes.append(
                f"Subtotal - discount + tax = {_fmt(expected_total)}, but the total is {_fmt(ext.total_amount)}."
            )

    return notes
