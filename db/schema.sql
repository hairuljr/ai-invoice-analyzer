-- Init script for PostgreSQL. The app also creates this table on startup
-- (SQLAlchemy create_all), so running this file manually is optional.
-- Usage: psql -d ai_invoice_analyzer -f db/schema.sql

CREATE TABLE IF NOT EXISTS invoices (
    id                SERIAL PRIMARY KEY,
    vendor_name       VARCHAR(255),
    invoice_number    VARCHAR(100),
    invoice_date      DATE,
    total_amount      NUMERIC(18, 2),
    currency          VARCHAR(3),
    item_description  TEXT,
    summary           TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- History is listed newest first.
CREATE INDEX IF NOT EXISTS ix_invoices_created_at ON invoices (created_at);
