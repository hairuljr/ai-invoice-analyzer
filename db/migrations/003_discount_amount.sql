-- Adds the invoice-level discount, used by the total check (subtotal - discount + tax = total).
-- Non-destructive and idempotent. Usage: psql -d ai_invoice_analyzer -f db/migrations/003_discount_amount.sql

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(18, 2);
