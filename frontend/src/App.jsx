import { useEffect, useState } from "react";
import { listInvoices, processInvoice } from "./api.js";

const MAX_MB = 10;
const ACCEPT = ".pdf,.jpg,.jpeg,.png";
const ITEMS_PER_PAGE = 5;

// Returns null for a missing amount, so callers decide how to show it ("-", "not found" or hidden).
function formatAmount(amount, currency) {
  if (amount == null) return null;
  try {
    return new Intl.NumberFormat("id-ID", { style: "currency", currency: currency || "IDR" }).format(amount);
  } catch {
    return `${currency ?? ""} ${amount}`; // unknown currency code from the LLM
  }
}

function UploadForm({ onProcessed }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file) return;
    // Quick client-side check for a friendly message; the backend validates again.
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`File too large. Maximum size is ${MAX_MB} MB.`);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const { invoice, reused } = await processInvoice(file);
      onProcessed(invoice, reused);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Upload invoice</h2>
      <input type="file" accept={ACCEPT} onChange={(e) => setFile(e.target.files[0] ?? null)} />
      <button type="submit" disabled={!file || loading}>
        {loading ? "Processing with AI..." : "Process invoice"}
      </button>
      <p className="hint">PDF, JPG or PNG, max {MAX_MB} MB.</p>
      {error && <p className="error">{error}</p>}
    </form>
  );
}

function ReviewBadge({ invoice }) {
  return invoice.needs_review ? (
    <span className="badge warn">Needs review</span>
  ) : (
    <span className="badge ok">Checks passed</span>
  );
}

// Client-side pagination: all items are already in the response, we only show one page at a time.
// The parent passes key={invoice.id}, so the page resets to 1 when another invoice is shown.
function LineItems({ items, currency }) {
  const [page, setPage] = useState(0);
  if (items.length === 0) return null;

  const pageCount = Math.ceil(items.length / ITEMS_PER_PAGE);
  const start = page * ITEMS_PER_PAGE;
  const visible = items.slice(start, start + ITEMS_PER_PAGE);

  return (
    <>
      <table className="items">
        <thead>
          <tr>
            <th>Item</th>
            <th className="num">Qty</th>
            <th className="num">Unit price</th>
            <th className="num">Amount</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((item, i) => (
            <tr key={start + i}>
              <td>{item.description ?? "-"}</td>
              <td className="num">{item.quantity ?? "-"}</td>
              <td className="num">{formatAmount(item.unit_price, currency) ?? "-"}</td>
              <td className="num">{formatAmount(item.amount, currency) ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {pageCount > 1 && (
        <div className="pager">
          <button type="button" onClick={() => setPage(page - 1)} disabled={page === 0}>
            Prev
          </button>
          <span>
            Items {start + 1}-{start + visible.length} of {items.length}
          </span>
          <button type="button" onClick={() => setPage(page + 1)} disabled={page === pageCount - 1}>
            Next
          </button>
        </div>
      )}
    </>
  );
}

function ResultCard({ invoice, reused }) {
  const rows = [
    ["Vendor", invoice.vendor_name],
    ["Invoice number", invoice.invoice_number],
    ["Invoice date", invoice.invoice_date],
    ["Items", invoice.item_description],
    // Optional breakdown lines (third element true) are hidden when the invoice has none;
    // required fields stay visible and show "not found".
    ["Subtotal", formatAmount(invoice.subtotal, invoice.currency), true],
    ["Discount", formatAmount(invoice.discount_amount, invoice.currency), true],
    ["Tax", formatAmount(invoice.tax_amount, invoice.currency), true],
    ["Total amount", formatAmount(invoice.total_amount, invoice.currency)],
    ["File", invoice.original_filename],
  ].filter(([, value, optional]) => !(optional && value == null));
  return (
    <section className="card">
      <h2>
        Result #{invoice.id} <ReviewBadge invoice={invoice} />
      </h2>
      {reused && <p className="hint">This file was already processed, showing the stored result (no new AI call).</p>}
      {invoice.review_notes.length > 0 && (
        <ul className="notes">
          {invoice.review_notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
      <p className="summary">{invoice.summary}</p>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value ?? <span className="missing">not found</span>}</dd>
          </div>
        ))}
      </dl>
      <LineItems key={invoice.id} items={invoice.line_items} currency={invoice.currency} />
    </section>
  );
}

function HistoryTable({ invoices, selectedId, onSelect }) {
  if (invoices.length === 0) return <p className="hint">No invoices processed yet.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Vendor</th>
          <th>Invoice no.</th>
          <th>Date</th>
          <th className="num">Total</th>
          <th>Status</th>
          <th>Processed at</th>
        </tr>
      </thead>
      <tbody>
        {invoices.map((inv) => (
          <tr key={inv.id} className={inv.id === selectedId ? "selected" : ""} onClick={() => onSelect(inv)}>
            <td>{inv.id}</td>
            <td>{inv.vendor_name ?? "-"}</td>
            <td>{inv.invoice_number ?? "-"}</td>
            <td>{inv.invoice_date ?? "-"}</td>
            <td className="num">{formatAmount(inv.total_amount, inv.currency) ?? "-"}</td>
            <td>
              <ReviewBadge invoice={inv} />
            </td>
            <td>{new Date(inv.created_at).toLocaleString("id-ID")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function App() {
  const [invoices, setInvoices] = useState([]);
  const [selected, setSelected] = useState(null);
  const [reused, setReused] = useState(false);
  const [historyError, setHistoryError] = useState("");

  useEffect(() => {
    listInvoices()
      .then(setInvoices)
      .catch((err) => setHistoryError(err.message));
  }, []);

  function handleProcessed(invoice, wasReused) {
    setSelected(invoice);
    setReused(wasReused);
    // Newest first, no refetch needed. A reused result is already in the list.
    if (!wasReused) setInvoices((prev) => [invoice, ...prev]);
  }

  function handleSelect(invoice) {
    setSelected(invoice);
    setReused(false);
  }

  return (
    <main>
      <h1>AI Invoice Analyzer</h1>
      <div className="top">
        <UploadForm onProcessed={handleProcessed} />
        {selected ? <ResultCard invoice={selected} reused={reused} /> : <section className="card hint">Upload an invoice to see the extracted data.</section>}
      </div>
      <h2>History</h2>
      {historyError ? (
        <p className="error">{historyError}</p>
      ) : (
        <HistoryTable invoices={invoices} selectedId={selected?.id} onSelect={handleSelect} />
      )}
    </main>
  );
}
