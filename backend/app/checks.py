"""Deterministic checks on the LLM output. Code verifies the arithmetic; the LLM only reads.

Anything suspicious becomes a review note, and an invoice with notes is flagged for manual review
instead of being rejected: finance still gets the data, but knows not to trust it blindly.
Notes are in Bahasa Indonesia with Indonesian number format, like the summary and the UI amounts.
"""

from .schemas import InvoiceExtraction

REQUIRED_FIELDS = {
    "vendor_name": "nama vendor",
    "invoice_number": "nomor invoice",
    "invoice_date": "tanggal invoice",
    "total_amount": "total",
}
# Absolute, not relative: 0.1% of Rp7,000,000 would hide a Rp7,000 error. 1 unit covers tax rounding.
TOLERANCE = 1.0
CHECK_SOURCE = "Periksa dokumen asli."


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE


def _number(n: float) -> str:
    """Indonesian format: 6993000 -> '6.993.000', 3560.75 -> '3.560,75'."""
    text = f"{n:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return text.removesuffix(",00")


def _quantity(q: float) -> str:
    """Quantities are not money: 50.0 -> '50', 1.5 -> '1,5'."""
    return f"{q:.10g}".replace(".", ",")  # .10g: no scientific notation for normal quantities


def _money(n: float, currency: str | None) -> str:
    prefix = "Rp " if currency in (None, "IDR") else f"{currency} "
    return prefix + _number(n)


def review_notes(ext: InvoiceExtraction) -> list[str]:
    notes = []

    def money(n: float) -> str:
        return _money(n, ext.currency)

    def mismatch(printed: float, computed: float) -> str:
        return f"(selisih {money(abs(printed - computed))}). {CHECK_SOURCE}"

    missing = [label for field, label in REQUIRED_FIELDS.items() if getattr(ext, field) is None]
    if missing:
        notes.append(f"Data tidak ditemukan: {', '.join(missing)}. Lengkapi dari dokumen asli.")

    for item in ext.line_items:
        if None not in (item.quantity, item.unit_price, item.amount):
            computed = item.quantity * item.unit_price
            if not _close(computed, item.amount):
                notes.append(
                    f"Baris '{item.description}': {_quantity(item.quantity)} x {money(item.unit_price)}"
                    f" = {money(computed)}, tetapi tercetak {money(item.amount)} {mismatch(item.amount, computed)}"
                )

    amounts = [item.amount for item in ext.line_items]
    if amounts and None not in amounts and ext.subtotal is not None:
        computed = sum(amounts)
        if not _close(computed, ext.subtotal):
            notes.append(
                f"Jumlah baris item {money(computed)}, tetapi subtotal tercetak {money(ext.subtotal)}"
                f" {mismatch(ext.subtotal, computed)}"
            )

    if ext.subtotal is not None and ext.total_amount is not None:
        computed = ext.subtotal - (ext.discount_amount or 0) + (ext.tax_amount or 0)
        if not _close(computed, ext.total_amount):
            notes.append(
                f"Total tercetak {money(ext.total_amount)}, tetapi subtotal - diskon + pajak = {money(computed)}"
                f" {mismatch(ext.total_amount, computed)}"
            )

    return notes
