// Thin wrappers around the backend REST API. Errors surface the backend's "detail" message.

async function parse(response) {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body;
}

export async function processInvoice(file) {
  const form = new FormData();
  form.append("file", file);
  return parse(await fetch("/api/invoices/process", { method: "POST", body: form }));
}

export async function listInvoices() {
  return parse(await fetch("/api/invoices"));
}
