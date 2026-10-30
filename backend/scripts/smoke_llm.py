"""Smoke-test the single LLM extraction call against one file.

Run from backend/: .venv/bin/python -m scripts.smoke_llm ../samples/invoice_medika.pdf
"""

import mimetypes
import sys
import time
from pathlib import Path

from app.llm import extract_invoice


def main() -> None:
    path = Path(sys.argv[1])
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    start = time.perf_counter()
    result = extract_invoice(path.read_bytes(), mime, path.name)
    print(result.model_dump_json(indent=2))
    print(f"latency: {time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    main()
