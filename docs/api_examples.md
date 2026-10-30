# API examples (real responses, recorded 2026-10-30)

## POST /api/invoices/process (invoice_farma.pdf)

```bash
curl -F 'file=@samples/invoice_farma.pdf' http://localhost:8000/api/invoices/process
```

HTTP 201

```json
{
  "id": 2,
  "vendor_name": "CV Farma Nusantara",
  "invoice_number": "FN/2026/X/0042",
  "invoice_date": "2026-10-15",
  "total_amount": 6493500.0,
  "currency": "IDR",
  "item_description": "Paracetamol 500 mg (strip), Amoxicillin 500 mg (strip)",
  "summary": "CV Farma Nusantara menagihkan pembelian obat Paracetamol dan Amoxicillin kepada Rumah Sakit Contoh dengan total Rp 6.493.500.",
  "original_filename": "invoice_farma.pdf",
  "created_at": "2026-10-30T13:27:54.365904+07:00"
}
```

## POST /api/invoices/process (invoice_lab.jpg)

```bash
curl -F 'file=@samples/invoice_lab.jpg' http://localhost:8000/api/invoices/process
```

HTTP 201

```json
{
  "id": 3,
  "vendor_name": "PT Lab Diagnostik Prima",
  "invoice_number": "LDP-7781",
  "invoice_date": "2026-10-20",
  "total_amount": 12099000.0,
  "currency": "IDR",
  "item_description": "Reagen hematologi 1 L, Kalibrasi alat analyzer",
  "summary": "PT Lab Diagnostik Prima menagihkan reagen hematologi dan jasa kalibrasi alat analyzer sebesar Rp 12.099.000 kepada Rumah Sakit Contoh.",
  "original_filename": "invoice_lab.jpg",
  "created_at": "2026-10-30T13:28:01.001328+07:00"
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
    "vendor_name": "PT Lab Diagnostik Prima",
    "invoice_number": "LDP-7781",
    "invoice_date": "2026-10-20",
    "total_amount": 12099000.0,
    "currency": "IDR",
    "item_description": "Reagen hematologi 1 L, Kalibrasi alat analyzer",
    "summary": "PT Lab Diagnostik Prima menagihkan reagen hematologi dan jasa kalibrasi alat analyzer sebesar Rp 12.099.000 kepada Rumah Sakit Contoh.",
    "original_filename": "invoice_lab.jpg",
    "created_at": "2026-10-30T13:28:01.001328+07:00"
  },
  {
    "id": 2,
    "vendor_name": "CV Farma Nusantara",
    "invoice_number": "FN/2026/X/0042",
    "invoice_date": "2026-10-15",
    "total_amount": 6493500.0,
    "currency": "IDR",
    "item_description": "Paracetamol 500 mg (strip), Amoxicillin 500 mg (strip)",
    "summary": "CV Farma Nusantara menagihkan pembelian obat Paracetamol dan Amoxicillin kepada Rumah Sakit Contoh dengan total Rp 6.493.500.",
    "original_filename": "invoice_farma.pdf",
    "created_at": "2026-10-30T13:27:54.365904+07:00"
  },
  {
    "id": 1,
    "vendor_name": "PT Medika Sejahtera Abadi",
    "invoice_number": "INV-2026-00125",
    "invoice_date": "2026-10-01",
    "total_amount": 16594500.0,
    "currency": "IDR",
    "item_description": "Sarung tangan nitril (box), Masker bedah 3-ply (box), Spuit 3 ml (box)",
    "summary": "PT Medika Sejahtera Abadi menagihkan pembelian sarung tangan nitril, masker bedah, dan spuit dengan total sebesar Rp 16.594.500.",
    "original_filename": "invoice_medika.pdf",
    "created_at": "2026-10-30T13:24:36.598354+07:00"
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

