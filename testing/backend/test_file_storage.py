"""Tests for Supabase Storage upload/signed-URL helpers (core.storage)."""
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.exceptions import ValidationError

from core import storage

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de0000000c4944415408d763f8cfc0c0c0c00400023a0301a3a1adda00000"
    "00049454e44ae426082"
)


@pytest.fixture(autouse=True)
def reset_client_cache():
    storage._client = None
    yield
    storage._client = None


@pytest.fixture
def mock_supabase_client():
    client = MagicMock()
    with patch("core.storage.create_client", return_value=client):
        yield client


def test_upload_image_stores_under_server_generated_uuid_name(mock_supabase_client):
    bucket = mock_supabase_client.storage.from_.return_value
    file_obj = io.BytesIO(PNG_BYTES)

    with patch("core.storage.scan_for_malware"):
        object_key = storage.upload_image(file_obj, "../../etc/passwd.png")

    name, ext = object_key.rsplit(".", 1)
    uuid.UUID(name)  # raises ValueError if not a valid UUID
    assert ext == "png"
    assert object_key != "../../etc/passwd.png"
    bucket.upload.assert_called_once()
    uploaded_key = bucket.upload.call_args[0][0]
    assert uploaded_key == object_key


def test_upload_image_rejects_disallowed_content(mock_supabase_client):
    php_payload = io.BytesIO(b"<?php system($_GET['c']); ?>")
    with pytest.raises(ValidationError):
        storage.upload_image(php_payload, "shell.php")
    mock_supabase_client.storage.from_.return_value.upload.assert_not_called()


def test_get_signed_url_returns_url_from_supabase(mock_supabase_client, settings):
    settings.SUPABASE_STORAGE_BUCKET = "auction-images"
    bucket = mock_supabase_client.storage.from_.return_value
    bucket.create_signed_url.return_value = {"signedURL": "https://example.com/signed?token=abc"}

    url = storage.get_signed_url("some-key.png", expires_in=900)

    assert url == "https://example.com/signed?token=abc"
    bucket.create_signed_url.assert_called_once_with("some-key.png", 900)
