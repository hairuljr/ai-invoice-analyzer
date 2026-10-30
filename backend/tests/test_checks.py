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
    assert len(notes) == 1 and "Total tercetak Rp 7.000.000" in notes[0]


def test_sample_invoice_wrong_total_exact_note():
    # Same numbers as samples/invoice_wrong_total.pdf: the LLM copies the printed (wrong) total,
    # and code catches it. Note uses the UI's number format, states the gap and the next action.
    ext = make(
        line_items=[
            LineItem(description="Jasa sterilisasi instrumen (set)", quantity=120, unit_price=35_000, amount=4_200_000),
            LineItem(description="Indikator kimia sterilisasi (pack)", quantity=10, unit_price=210_000, amount=2_100_000),
        ],
        subtotal=6_300_000,
        tax_amount=693_000,
        total_amount=7_000_000,
        currency="IDR",
    )
    assert review_notes(ext) == [
        "Total tercetak Rp 7.000.000, tetapi subtotal - diskon + pajak = Rp 6.993.000"
        " (selisih Rp 7.000). Periksa dokumen asli."
    ]


def test_foreign_currency_and_decimals_are_formatted():
    items = [LineItem(description="MRI contrast", quantity=1.5, unit_price=185.5, amount=300)]
    ext = make(line_items=items, subtotal=300, tax_amount=None, total_amount=300, currency="USD")
    assert review_notes(ext) == [
        "Baris 'MRI contrast': 1,5 x USD 185,50 = USD 278,25, tetapi tercetak USD 300"
        " (selisih USD 21,75). Periksa dokumen asli."
    ]


def test_line_items_not_matching_subtotal_is_flagged():
    notes = review_notes(make(subtotal=9_000_000, total_amount=9_962_500))
    assert any("Jumlah baris item Rp 8.750.000, tetapi subtotal tercetak Rp 9.000.000 (selisih Rp 250.000)" in n for n in notes)


def test_wrong_line_amount_is_flagged():
    items = [LineItem(description="Gloves", quantity=50, unit_price=85_000, amount=4_000_000)]
    notes = review_notes(make(line_items=items, subtotal=4_000_000, tax_amount=0, total_amount=4_000_000))
    assert notes == [
        "Baris 'Gloves': 50 x Rp 85.000 = Rp 4.250.000, tetapi tercetak Rp 4.000.000"
        " (selisih Rp 250.000). Periksa dokumen asli."
    ]


def test_missing_required_fields_are_flagged():
    notes = review_notes(make(vendor_name=None, total_amount=None))
    assert notes == ["Data tidak ditemukan: nama vendor, total. Lengkapi dari dokumen asli."]


def test_no_tax_line_means_total_equals_subtotal():
    assert review_notes(make(tax_amount=None, total_amount=8_750_000)) == []


def test_incomplete_line_items_are_skipped_not_flagged():
    items = [LineItem(description="Service", amount=None)]
    assert review_notes(make(line_items=items)) == []


def test_discount_is_subtracted_before_comparing_total():
    # Real edge case: 5% discount, then 11% PPN on the discounted amount.
    ext = make(line_items=[], subtotal=137_352_000, discount_amount=6_867_600, tax_amount=14_353_284, total_amount=144_837_684)
    assert review_notes(ext) == []
