import pytest

from app.uploads import UploadError, validate_upload

MB = 1024 * 1024
PDF = b"%PDF-1.4 dummy"
PNG = b"\x89PNG\r\n\x1a\n dummy"
JPG = b"\xff\xd8\xff\xe0 dummy"


@pytest.mark.parametrize(
    "filename, data, expected",
    [
        ("invoice.pdf", PDF, "application/pdf"),
        ("scan.PNG", PNG, "image/png"),
        ("photo.jpeg", JPG, "image/jpeg"),
        ("photo.jpg", JPG, "image/jpeg"),
    ],
)
def test_accepts_supported_files(filename, data, expected):
    assert validate_upload(filename, data, MB) == expected


@pytest.mark.parametrize(
    "filename, data, status",
    [
        ("notes.txt", b"hello", 415),  # unsupported extension
        ("invoice.pdf", b"", 400),  # empty file
        ("invoice.pdf", PDF + b"x" * MB, 413),  # over the size limit
        ("invoice.pdf", PNG, 415),  # renamed PNG
        ("invoice.png", b"<html>", 415),  # not an image at all
    ],
)
def test_rejects_invalid_files(filename, data, status):
    with pytest.raises(UploadError) as exc:
        validate_upload(filename, data, MB)
    assert exc.value.status_code == status
