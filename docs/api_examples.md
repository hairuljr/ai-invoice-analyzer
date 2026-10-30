# API examples (real responses, recorded 2026-10-30)

## Process a PDF invoice

```bash
curl -F 'file=@samples/invoice_farma.pdf' http://localhost:8000/api/invoices/process
```

HTTP 201

```json
{
  "id": 1,
  "vendor_name": "CV Farma Nusantara",
  "invoice_number": "FN/2026/X/0042",
  "invoice_date": "2026-10-15",
  "currency": "IDR",
  "line_items": [
    {
      "description": "Paracetamol 500 mg (strip)",
      "quantity": 500.0,
      "unit_price": 4500.0,
      "amount": 2250000.0
    },
    {
      "description": "Amoxicillin 500 mg (strip)",
      "quantity": 300.0,
      "unit_price": 12000.0,
      "amount": 3600000.0
    }
  ],
  "subtotal": 5850000.0,
  "tax_amount": 643500.0,
  "total_amount": 6493500.0,
  "item_description": "Paracetamol 500 mg (strip) dan Amoxicillin 500 mg (strip)",
  "summary": "CV Farma Nusantara menagih pembayaran untuk Paracetamol 500 mg dan Amoxicillin 500 mg kepada Rumah Sakit Contoh sejumlah Rp 6.493.500.",
  "needs_review": false,
  "review_notes": [],
  "original_filename": "invoice_farma.pdf",
  "created_at": "2026-10-30T13:43:05.011114+07:00"
}
```

## Process a JPG invoice

```bash
curl -F 'file=@samples/invoice_lab.jpg' http://localhost:8000/api/invoices/process
```

HTTP 201

```json
{
  "id": 2,
  "vendor_name": "PT Lab Diagnostik Prima",
  "invoice_number": "LDP-7781",
  "invoice_date": "2026-10-20",
  "currency": "IDR",
  "line_items": [
    {
      "description": "Reagen hematologi 1 L",
      "quantity": 4.0,
      "unit_price": 2350000.0,
      "amount": 9400000.0
    },
    {
      "description": "Kalibrasi alat analyzer",
      "quantity": 1.0,
      "unit_price": 1500000.0,
      "amount": 1500000.0
    }
  ],
  "subtotal": 10900000.0,
  "tax_amount": 1199000.0,
  "total_amount": 12099000.0,
  "item_description": "Reagen hematologi 1 L dan kalibrasi alat analyzer",
  "summary": "PT Lab Diagnostik Prima menagihkan pembelian reagen hematologi dan jasa kalibrasi alat analyzer dengan total sebesar Rp 12.099.000.",
  "needs_review": false,
  "review_notes": [],
  "original_filename": "invoice_lab.jpg",
  "created_at": "2026-10-30T13:43:13.689963+07:00"
}
```

## Invoice whose printed total is wrong

The printed total does not equal subtotal + tax, so the invoice is stored but flagged `needs_review`.

```bash
curl -F 'file=@samples/invoice_wrong_total.pdf' http://localhost:8000/api/invoices/process
```

HTTP 201

```json
{
  "id": 3,
  "vendor_name": "PT Sarana Steril Indonesia",
  "invoice_number": "SSI-2026-0311",
  "invoice_date": "2026-10-22",
  "currency": "IDR",
  "line_items": [
    {
      "description": "Jasa sterilisasi instrumen (set)",
      "quantity": 120.0,
      "unit_price": 35000.0,
      "amount": 4200000.0
    },
    {
      "description": "Indikator kimia sterilisasi (pack)",
      "quantity": 10.0,
      "unit_price": 210000.0,
      "amount": 2100000.0
    }
  ],
  "subtotal": 6300000.0,
  "tax_amount": 693000.0,
  "total_amount": 7000000.0,
  "item_description": "Jasa sterilisasi instrumen dan indikator kimia sterilisasi",
  "summary": "PT Sarana Steril Indonesia menagihkan biaya jasa sterilisasi instrumen dan indikator kimia sterilisasi dengan total tagihan sebesar Rp 7.000.000.",
  "needs_review": true,
  "review_notes": [
    "Subtotal + tax = 6,993,000, but the total is 7,000,000."
  ],
  "original_filename": "invoice_wrong_total.pdf",
  "created_at": "2026-10-30T13:43:22.342328+07:00"
}
```

## Same file uploaded again

HTTP 200 instead of 201: the stored result is returned and the AI is not called again.

```bash
curl -F 'file=@samples/invoice_wrong_total.pdf' http://localhost:8000/api/invoices/process
```

HTTP 200

```json
{
  "id": 3,
  "vendor_name": "PT Sarana Steril Indonesia",
  "invoice_number": "SSI-2026-0311",
  "invoice_date": "2026-10-22",
  "currency": "IDR",
  "line_items": [
    {
      "description": "Jasa sterilisasi instrumen (set)",
      "quantity": 120.0,
      "unit_price": 35000.0,
      "amount": 4200000.0
    },
    {
      "description": "Indikator kimia sterilisasi (pack)",
      "quantity": 10.0,
      "unit_price": 210000.0,
      "amount": 2100000.0
    }
  ],
  "subtotal": 6300000.0,
  "tax_amount": 693000.0,
  "total_amount": 7000000.0,
  "item_description": "Jasa sterilisasi instrumen dan indikator kimia sterilisasi",
  "summary": "PT Sarana Steril Indonesia menagihkan biaya jasa sterilisasi instrumen dan indikator kimia sterilisasi dengan total tagihan sebesar Rp 7.000.000.",
  "needs_review": true,
  "review_notes": [
    "Subtotal + tax = 6,993,000, but the total is 7,000,000."
  ],
  "original_filename": "invoice_wrong_total.pdf",
  "created_at": "2026-10-30T13:43:22.342328+07:00"
}
```

## GET /api/invoices

```bash
curl http://localhost:8000/api/invoices
```

HTTP 200

```json
[
  {
    "id": 3,
    "vendor_name": "PT Sarana Steril Indonesia",
    "invoice_number": "SSI-2026-0311",
    "invoice_date": "2026-10-22",
    "currency": "IDR",
    "line_items": [
      {
        "description": "Jasa sterilisasi instrumen (set)",
        "quantity": 120.0,
        "unit_price": 35000.0,
        "amount": 4200000.0
      },
      {
        "description": "Indikator kimia sterilisasi (pack)",
        "quantity": 10.0,
        "unit_price": 210000.0,
        "amount": 2100000.0
      }
    ],
    "subtotal": 6300000.0,
    "tax_amount": 693000.0,
    "total_amount": 7000000.0,
    "item_description": "Jasa sterilisasi instrumen dan indikator kimia sterilisasi",
    "summary": "PT Sarana Steril Indonesia menagihkan biaya jasa sterilisasi instrumen dan indikator kimia sterilisasi dengan total tagihan sebesar Rp 7.000.000.",
    "needs_review": true,
    "review_notes": [
      "Subtotal + tax = 6,993,000, but the total is 7,000,000."
    ],
    "original_filename": "invoice_wrong_total.pdf",
    "created_at": "2026-10-30T13:43:22.342328+07:00"
  },
  {
    "id": 2,
    "vendor_name": "PT Lab Diagnostik Prima",
    "invoice_number": "LDP-7781",
    "invoice_date": "2026-10-20",
    "currency": "IDR",
    "line_items": [
      {
        "description": "Reagen hematologi 1 L",
        "quantity": 4.0,
        "unit_price": 2350000.0,
        "amount": 9400000.0
      },
      {
        "description": "Kalibrasi alat analyzer",
        "quantity": 1.0,
        "unit_price": 1500000.0,
        "amount": 1500000.0
      }
    ],
    "subtotal": 10900000.0,
    "tax_amount": 1199000.0,
    "total_amount": 12099000.0,
    "item_description": "Reagen hematologi 1 L dan kalibrasi alat analyzer",
    "summary": "PT Lab Diagnostik Prima menagihkan pembelian reagen hematologi dan jasa kalibrasi alat analyzer dengan total sebesar Rp 12.099.000.",
    "needs_review": false,
    "review_notes": [],
    "original_filename": "invoice_lab.jpg",
    "created_at": "2026-10-30T13:43:13.689963+07:00"
  },
  {
    "id": 1,
    "vendor_name": "CV Farma Nusantara",
    "invoice_number": "FN/2026/X/0042",
    "invoice_date": "2026-10-15",
    "currency": "IDR",
    "line_items": [
      {
        "description": "Paracetamol 500 mg (strip)",
        "quantity": 500.0,
        "unit_price": 4500.0,
        "amount": 2250000.0
      },
      {
        "description": "Amoxicillin 500 mg (strip)",
        "quantity": 300.0,
        "unit_price": 12000.0,
        "amount": 3600000.0
      }
    ],
    "subtotal": 5850000.0,
    "tax_amount": 643500.0,
    "total_amount": 6493500.0,
    "item_description": "Paracetamol 500 mg (strip) dan Amoxicillin 500 mg (strip)",
    "summary": "CV Farma Nusantara menagih pembayaran untuk Paracetamol 500 mg dan Amoxicillin 500 mg kepada Rumah Sakit Contoh sejumlah Rp 6.493.500.",
    "needs_review": false,
    "review_notes": [],
    "original_filename": "invoice_farma.pdf",
    "created_at": "2026-10-30T13:43:05.011114+07:00"
  }
]
```

## Error: unsupported file

```bash
curl -F 'file=@notes.txt' http://localhost:8000/api/invoices/process
```

HTTP 415

```json
{
  "detail": "Unsupported file type. Upload a PDF, JPG or PNG invoice."
}
```

## Error: renamed / corrupt file

```bash
curl -F 'file=@fake.pdf' http://localhost:8000/api/invoices/process
```

HTTP 415

```json
{
  "detail": "File content does not match its extension (corrupt or renamed file?)."
}
```

## Error: unknown invoice

```bash
curl http://localhost:8000/api/invoices/9999
```

HTTP 404

```json
{
  "detail": "Invoice not found"
}
```

