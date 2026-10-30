from app.checks import review_notes
from app.schemas import InvoiceExtraction, LineItem


def make(**overrides) -> InvoiceExtraction:
    data = dict(
        vendor_name="PT Medika",
        invoice_number="INV-1",
        invoice_date="2026-10-01",
        line_items=[
            LineItem(description="Gloves", quantity=50, unit_price=85_000, amount=4_250_000),
            LineItem(description="Masks", quantity=100, unit_price=45_000, amount=4_500_000),
        ],
        subtotal=8_750_000,
        tax_amount=962_500,
        total_amount=9_712_500,
        summary="s",
    )
    return InvoiceExtraction(**{**data, **overrides})


def test_consistent_invoice_has_no_notes():
    assert review_notes(make()) == []


def test_rounding_within_tolerance_is_accepted():
    assert review_notes(make(tax_amount=962_500.4, total_amount=9_712_501)) == []


def test_wrong_total_is_flagged():
    notes = review_notes(make(total_amount=7_000_000))
    assert len(notes) == 1 and "total is 7,000,000" in notes[0]


def test_line_items_not_matching_subtotal_is_flagged():
    notes = review_notes(make(subtotal=9_000_000, total_amount=9_962_500))
    assert any("Line items add up to 8,750,000" in n for n in notes)


def test_wrong_line_amount_is_flagged():
    items = [LineItem(description="Gloves", quantity=50, unit_price=85_000, amount=4_000_000)]
    notes = review_notes(make(line_items=items, subtotal=4_000_000, tax_amount=0, total_amount=4_000_000))
    assert notes == ["Line 'Gloves': 50 x 85,000 = 4,250,000, but the invoice says 4,000,000."]


def test_missing_required_fields_are_flagged():
    notes = review_notes(make(vendor_name=None, total_amount=None))
    assert notes == ["Missing fields: vendor_name, total_amount."]


def test_no_tax_line_means_total_equals_subtotal():
    assert review_notes(make(tax_amount=None, total_amount=8_750_000)) == []


def test_incomplete_line_items_are_skipped_not_flagged():
    items = [LineItem(description="Service", amount=None)]
    assert review_notes(make(line_items=items)) == []


def test_discount_is_subtracted_before_comparing_total():
    # Real edge case: 5% discount, then 11% PPN on the discounted amount.
    ext = make(line_items=[], subtotal=137_352_000, discount_amount=6_867_600, tax_amount=14_353_284, total_amount=144_837_684)
    assert review_notes(ext) == []
