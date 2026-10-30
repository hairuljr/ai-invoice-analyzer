"""Evaluate extraction accuracy against a small golden set (samples/expected.json).

Run from backend/: .venv/bin/python -m scripts.evaluate
Calls the real LLM. Free-text fields (item_description, summary) are only checked for presence.
"""

import json
import mimetypes
import time
from pathlib import Path

from app.llm import ExtractionError, extract_invoice

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
FIELDS = ["vendor_name", "invoice_number", "invoice_date", "total_amount", "currency"]


def matches(field: str, expected, actual) -> bool:
    if actual is None:
        return False
    if field == "total_amount":
        return abs(float(actual) - expected) < 1
    if field == "vendor_name":
        return str(actual).strip().lower() == expected.lower()
    return str(actual) == str(expected)


def main() -> None:
    golden = json.loads((SAMPLES / "expected.json").read_text())
    correct = {field: 0 for field in FIELDS}
    for filename, expected in golden.items():
        path = SAMPLES / filename
        start = time.perf_counter()
        try:
            result = extract_invoice(path.read_bytes(), mimetypes.guess_type(filename)[0]).model_dump(mode="json")
        except ExtractionError as e:
            print(f"{filename}: FAILED ({e})")
            continue
        wrong = []
        for field in FIELDS:
            if matches(field, expected[field], result[field]):
                correct[field] += 1
            else:
                wrong.append(f"{field}={result[field]!r} (expected {expected[field]!r})")
        has_text = bool(result["item_description"]) and bool(result["summary"])
        status = "OK" if not wrong and has_text else "MISMATCH " + "; ".join(wrong)
        print(f"{filename}: {status} [{time.perf_counter() - start:.1f}s]")

    print("\nField accuracy:")
    for field in FIELDS:
        print(f"  {field:<15} {correct[field]}/{len(golden)}")


if __name__ == "__main__":
    main()
