-- Adds line items, subtotal/tax, review flag and file hash to an existing invoices table.
-- Non-destructive and idempotent. Usage: psql -d ai_invoice_analyzer -f db/migrations/002_review_and_line_items.sql

ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS line_items   JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS subtotal     NUMERIC(18, 2),
    ADD COLUMN IF NOT EXISTS tax_amount   NUMERIC(18, 2),
    ADD COLUMN IF NOT EXISTS needs_review BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS review_notes JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS file_sha256  VARCHAR(64);

-- In case the columns were added earlier without defaults.
UPDATE invoices SET line_items = '[]' WHERE line_items IS NULL;
UPDATE invoices SET review_notes = '[]' WHERE review_notes IS NULL;
ALTER TABLE invoices
    ALTER COLUMN line_items SET DEFAULT '[]',
    ALTER COLUMN line_items SET NOT NULL,
    ALTER COLUMN review_notes SET DEFAULT '[]',
    ALTER COLUMN review_notes SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_invoices_file_sha256 ON invoices (file_sha256);
