"""Evaluate extraction accuracy against a small golden set (samples/expected.json).

Run from backend/: .venv/bin/python -m scripts.evaluate
Calls the real LLM. Free-text fields (item_description, summary) are only checked for presence.
`needs_review` checks the arithmetic checks: a deliberately wrong invoice must be flagged, clean ones must not.
"""

import json
import mimetypes
import time
from pathlib import Path

from app.checks import review_notes
from app.llm import ExtractionError, extract_invoice

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
FIELDS = ["vendor_name", "invoice_number", "invoice_date", "subtotal", "tax_amount", "total_amount", "currency"]
AMOUNT_FIELDS = {"subtotal", "tax_amount", "total_amount"}


def matches(field: str, expected, actual) -> bool:
    if actual is None:
        return False
    if field in AMOUNT_FIELDS:
        return abs(float(actual) - expected) < 1
    if field == "vendor_name":
        return str(actual).strip().lower() == expected.lower()
    return str(actual) == str(expected)


def main() -> None:
    golden = json.loads((SAMPLES / "expected.json").read_text())
    correct = {field: 0 for field in [*FIELDS, "needs_review"]}
    for filename, expected in golden.items():
        path = SAMPLES / filename
        start = time.perf_counter()
        try:
            extracted = extract_invoice(path.read_bytes(), mimetypes.guess_type(filename)[0])
        except ExtractionError as e:
            print(f"{filename}: FAILED ({e})")
            continue
        result = extracted.model_dump(mode="json")
        result["needs_review"] = bool(review_notes(extracted))

        wrong = []
        for field in [*FIELDS, "needs_review"]:
            ok = result[field] == expected[field] if field == "needs_review" else matches(field, expected[field], result[field])
            if ok:
                correct[field] += 1
            else:
                wrong.append(f"{field}={result[field]!r} (expected {expected[field]!r})")
        has_text = bool(result["item_description"]) and bool(result["summary"])
        status = "OK" if not wrong and has_text else "MISMATCH " + "; ".join(wrong)
        print(f"{filename}: {status} [{time.perf_counter() - start:.1f}s]")

    print("\nField accuracy:")
    for field, count in correct.items():
        print(f"  {field:<15} {count}/{len(golden)}")


if __name__ == "__main__":
    main()
