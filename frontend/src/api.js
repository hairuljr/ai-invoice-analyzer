// Thin wrappers around the backend REST API. Errors surface the backend's "detail" message.

async function parse(response) {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body;
}

// Returns { invoice, reused }. The backend answers 200 instead of 201 when this exact file
// was processed before and the stored result is returned without calling the AI again.
export async function processInvoice(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/invoices/process", { method: "POST", body: form });
  return { invoice: await parse(response), reused: response.status === 200 };
}

export async function listInvoices() {
  return parse(await fetch("/api/invoices"));
}
