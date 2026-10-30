"""Upload validation. Pure functions, so they are unit-testable without HTTP."""

from pathlib import Path

ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

# File signatures ("magic bytes"). We trust the content, not the client's Content-Type header.
SIGNATURES = {
    b"%PDF-": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
}


class UploadError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def sniff_mime(data: bytes) -> str | None:
    for signature, mime in SIGNATURES.items():
        if data.startswith(signature):
            return mime
    return None


def validate_upload(filename: str, data: bytes, max_bytes: int) -> str:
    """Return the file's MIME type, or raise UploadError with an HTTP status and message."""
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadError(415, "Unsupported file type. Upload a PDF, JPG or PNG invoice.")
    if not data:
        raise UploadError(400, "The uploaded file is empty.")
    if len(data) > max_bytes:
        raise UploadError(413, f"File too large. Maximum size is {max_bytes // (1024 * 1024)} MB.")
    if sniff_mime(data) != ALLOWED_EXTENSIONS[extension]:
        raise UploadError(415, "File content does not match its extension (corrupt or renamed file?).")
    return ALLOWED_EXTENSIONS[extension]
