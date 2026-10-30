import { useEffect, useState } from "react";
import { listInvoices, processInvoice } from "./api.js";

const MAX_MB = 10;
const ACCEPT = ".pdf,.jpg,.jpeg,.png";

function formatAmount(amount, currency) {
  if (amount == null) return "-";
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
      onProcessed(await processInvoice(file));
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

function ResultCard({ invoice }) {
  const rows = [
    ["Vendor", invoice.vendor_name],
    ["Invoice number", invoice.invoice_number],
    ["Invoice date", invoice.invoice_date],
    ["Total amount", formatAmount(invoice.total_amount, invoice.currency)],
    ["Items", invoice.item_description],
    ["File", invoice.original_filename],
  ];
  return (
    <section className="card">
      <h2>Result #{invoice.id}</h2>
      <p className="summary">{invoice.summary}</p>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value ?? <span className="missing">not found</span>}</dd>
          </div>
        ))}
      </dl>
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
            <td className="num">{formatAmount(inv.total_amount, inv.currency)}</td>
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
  const [historyError, setHistoryError] = useState("");

  useEffect(() => {
    listInvoices()
      .then(setInvoices)
      .catch((err) => setHistoryError(err.message));
  }, []);

  function handleProcessed(invoice) {
    setSelected(invoice);
    setInvoices((prev) => [invoice, ...prev]); // newest first, no refetch needed
  }

  return (
    <main>
      <h1>AI Invoice Analyzer</h1>
      <div className="top">
        <UploadForm onProcessed={handleProcessed} />
        {selected ? <ResultCard invoice={selected} /> : <section className="card hint">Upload an invoice to see the extracted data.</section>}
      </div>
      <h2>History</h2>
      {historyError ? (
        <p className="error">{historyError}</p>
      ) : (
        <HistoryTable invoices={invoices} selectedId={selected?.id} onSelect={setSelected} />
      )}
    </main>
  );
}
