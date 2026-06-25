"""Tests for server-side upload validation (core.validators)."""
import io

import pytest
from rest_framework.exceptions import ValidationError

from core.validators import (
    DEFAULT_MAX_UPLOAD_BYTES,
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
)

# Minimal valid 1x1 PNG.
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415408d763f8cfc0c0c0c00400023a0301a3a1adda00000"
    "00049454e44ae426082"
)


def test_validate_mime_type_accepts_real_png():
    assert validate_mime_type(io.BytesIO(PNG_BYTES)) == "image/png"


def test_validate_mime_type_rejects_non_image_content():
    # Content is PHP source despite any client-supplied filename/extension;
    # detection must be based on actual bytes, not metadata.
    php_payload = io.BytesIO(b"<?php system($_GET['c']); ?>")
    with pytest.raises(ValidationError):
        validate_mime_type(php_payload)


@pytest.mark.parametrize("filename", ["shell.php", "config.env", "backup.bak", "session.swp", "repo.git"])
def test_validate_file_extension_blocks_dangerous_extensions(filename):
    with pytest.raises(ValidationError):
        validate_file_extension(filename)


@pytest.mark.parametrize("filename", ["photo.jpg", "photo.jpeg", "photo.png", "photo.webp", "photo.gif"])
def test_validate_file_extension_allows_image_extensions(filename):
    validate_file_extension(filename)


def test_validate_file_extension_rejects_mismatched_mime():
    with pytest.raises(ValidationError):
        validate_file_extension("photo.png", detected_mime="image/jpeg")


def test_validate_file_size_within_limit():
    small_file = io.BytesIO(b"x" * 100)
    assert validate_file_size(small_file) == 100


def test_validate_file_size_rejects_oversized_file():
    oversized = io.BytesIO(b"x" * (DEFAULT_MAX_UPLOAD_BYTES + 1))
    with pytest.raises(ValidationError):
        validate_file_size(oversized)
