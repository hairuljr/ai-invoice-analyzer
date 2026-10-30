-- Init script for PostgreSQL. The app also creates this table on startup
-- (SQLAlchemy create_all), so running this file manually is optional.
-- Usage: psql -d ai_invoice_analyzer -f db/schema.sql
-- Upgrading a database created by an earlier version: run db/migrations/*.sql in order.

CREATE TABLE IF NOT EXISTS invoices (
    id                SERIAL PRIMARY KEY,
    vendor_name       VARCHAR(255),
    invoice_number    VARCHAR(100),
    invoice_date      DATE,
    currency          VARCHAR(3),
    line_items        JSONB NOT NULL DEFAULT '[]',
    subtotal          NUMERIC(18, 2),
    discount_amount   NUMERIC(18, 2),
    tax_amount        NUMERIC(18, 2),
    total_amount      NUMERIC(18, 2),
    item_description  TEXT,
    summary           TEXT NOT NULL,
    needs_review      BOOLEAN NOT NULL DEFAULT false,
    review_notes      JSONB NOT NULL DEFAULT '[]',
    original_filename VARCHAR(255) NOT NULL,
    file_sha256       VARCHAR(64),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- History is listed newest first.
CREATE INDEX IF NOT EXISTS ix_invoices_created_at ON invoices (created_at);
-- Lookup for "same file uploaded again".
CREATE INDEX IF NOT EXISTS ix_invoices_file_sha256 ON invoices (file_sha256);
