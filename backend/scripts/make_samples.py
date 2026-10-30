"""Generate dummy invoices (fictional data, no real vendors/patients) into ../samples.

Run from backend/: .venv/bin/python scripts/make_samples.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parents[2] / "samples"

INVOICES = [
    {
        "file": "invoice_medika.pdf",
        "vendor": "PT Medika Sejahtera Abadi",
        "address": "Jl. Gatot Subroto No. 12, Jakarta Selatan",
        "number": "INV-2026-00125",
        "date": "01 Oktober 2026",
        "due": "31 Oktober 2026",
        "items": [
            ("Sarung tangan nitril (box)", 50, 85_000),
            ("Masker bedah 3-ply (box)", 100, 45_000),
            ("Spuit 3 ml (box)", 40, 155_000),
        ],
    },
    {
        "file": "invoice_farma.pdf",
        "vendor": "CV Farma Nusantara",
        "address": "Jl. Pahlawan Seribu Blok C3, BSD, Tangerang Selatan",
        "number": "FN/2026/X/0042",
        "date": "15 Oktober 2026",
        "due": "14 November 2026",
        "items": [
            ("Paracetamol 500 mg (strip)", 500, 4_500),
            ("Amoxicillin 500 mg (strip)", 300, 12_000),
        ],
    },
    {
        "file": "invoice_lab.jpg",
        "vendor": "PT Lab Diagnostik Prima",
        "address": "Jl. Raya Serpong Km 7, Tangerang",
        "number": "LDP-7781",
        "date": "20 Oktober 2026",
        "due": "19 November 2026",
        "items": [
            ("Reagen hematologi 1 L", 4, 2_350_000),
            ("Kalibrasi alat analyzer", 1, 1_500_000),
        ],
    },
]

TAX_RATE = 0.11


def rupiah(n: float) -> str:
    return "Rp " + f"{n:,.0f}".replace(",", ".")


def lines_for(inv: dict) -> list[str]:
    subtotal = sum(q * p for _, q, p in inv["items"])
    tax = subtotal * TAX_RATE
    rows = [
        inv["vendor"],
        inv["address"],
        "",
        "INVOICE",
        f"No. Invoice : {inv['number']}",
        f"Tanggal     : {inv['date']}",
        f"Jatuh Tempo : {inv['due']}",
        "Kepada      : Rumah Sakit Contoh (dummy)",
        "",
        "Deskripsi                         Qty      Harga          Jumlah",
    ]
    for name, qty, price in inv["items"]:
        rows.append(f"{name:<32}{qty:>5}  {rupiah(price):>13}  {rupiah(qty * price):>15}")
    rows += [
        "",
        f"{'Subtotal':<53}{rupiah(subtotal):>15}",
        f"{'PPN 11%':<53}{rupiah(tax):>15}",
        f"{'TOTAL':<53}{rupiah(subtotal + tax):>15}",
    ]
    return rows


def write_pdf(path: Path, rows: list[str]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    y = A4[1] - 60
    for i, row in enumerate(rows):
        is_vendor_line = i == 0
        bold = is_vendor_line or row.startswith(("INVOICE", "TOTAL"))
        c.setFont("Courier-Bold" if bold else "Courier", 14 if is_vendor_line else 10)
        c.drawString(50, y, row)
        y -= 18
    c.save()


def write_jpg(path: Path, rows: list[str]) -> None:
    img = Image.new("RGB", (1240, 60 + 34 * len(rows)), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=24)
    for i, row in enumerate(rows):
        draw.text((40, 30 + 34 * i), row, fill="black", font=font)
    img.save(path, "JPEG", quality=90)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for inv in INVOICES:
        rows = lines_for(inv)
        path = OUT / inv["file"]
        if path.suffix == ".jpg":
            write_jpg(path, rows)
        else:
            write_pdf(path, rows)
        print("wrote", path)


if __name__ == "__main__":
    main()
