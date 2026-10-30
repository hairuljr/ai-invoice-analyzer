# Edge-case test report (2026-10-30)

13 files, uploaded through the real HTTP API (`POST /api/invoices/process`) with the real LLM, against a separate
throwaway database. Expected values were defined beforehand per file. Review notes are quoted in their current
wording (they were translated to Bahasa Indonesia after this run; the checks themselves did not change).

## Results

| File | What it tests | HTTP | Result | Verdict |
|---|---|---|---|---|
| 01_complex_multipage_discount_dp.pdf | 3 pages, 60 lines, 3 different dates, 5% discount, down payment | 201 | Vendor, number and invoice date (not PO/due date) correct; 60/60 lines; discount 6,867,600; total = grand total 144,837,684; no review flag. About 30 s. | Pass (after fix 1) |
| 02_english_usd_decimal.pdf | USD, decimals, English | 201 | 3560.75 USD | Pass |
| 03_indo_decimal_format.pdf | Indonesian format `4.678.661,10` | 201 | 4678661.1 IDR | Pass |
| 04_missing_fields.pdf | No invoice number or date | 201 | Both `null` (not invented), flagged "Data tidak ditemukan: nomor invoice, tanggal invoice. Lengkapi dari dokumen asli." | Pass |
| 05_not_an_invoice.pdf | An internal memo | 422 | "This document does not look like an invoice. AI says: ... Surat Edaran Internal ..." Not stored. | Pass (after fixes 2 and 3) |
| 06_many_items_description.pdf | Many items | 201 | Description summarises all items, not only the first | Pass |
| 07_skewed_noisy_scan.jpg | Skewed, noisy scan | 201 | All fields correct | Pass |
| 08_low_res_photo.png | Low-resolution photo of the same invoice as 07 | 201 | All fields correct; flagged "Kemungkinan duplikat invoice #..." because 07 was already recorded | Pass (duplicate flag is correct) |
| invalid_01_fake.pdf | Text renamed to .pdf | 415 | "File content does not match its extension" | Pass |
| invalid_02_empty.pdf | Empty file | 400 | "The uploaded file is empty." | Pass |
| invalid_03_unsupported.txt | .txt | 415 | "Unsupported file type." | Pass |
| invalid_04_oversize.pdf | 11 MB | 413 | "File too large. Maximum size is 10 MB." | Pass |
| invalid_05_ext_spoof.pdf | JPEG renamed to .pdf | 415 | Rejected: content and extension disagree (decision in DECISIONS.md) | Pass |

## Fixes made because of this run

1. **Discount false positive (01).** The total check was `subtotal + tax = total`, so a correct invoice with a
   5% discount was flagged. Added `discount_amount` (schema, prompt, DB migration 003) and changed the check to
   `subtotal - discount + tax = total`. The prompt now also states that `total_amount` is the grand total, not
   the balance after a down payment.
2. **Non-invoice stored as an empty invoice (05).** Added `is_invoice` to the extraction; `false` returns `422`
   with the model's explanation and nothing is stored.
3. **Non-invoice caused a 502 (found after fix 2).** The model returned `line_items: null` for the memo, which
   failed validation twice. The schema now treats a null list as `[]`. Covered by a unit test.

The golden-set evaluation was re-run after these changes: still 4/4 on every field (no regression).
