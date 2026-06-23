"""Supabase Storage helpers for uploading and serving listing images."""
import os

from supabase import create_client

BUCKET = "listing-images"


def _client():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to use cloud storage."
        )
    return create_client(url, key)


def upload_file(file_path: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Upload *data* to Supabase Storage at *file_path* and return the stored path."""
    _client().storage.from_(BUCKET).upload(
        file_path,
        data,
        {"content-type": content_type, "upsert": "false"},
    )
    return file_path


def get_public_url(file_path: str) -> str:
    """Return the permanent public URL for a file in the public bucket."""
    return _client().storage.from_(BUCKET).get_public_url(file_path)


def get_signed_url(file_path: str, expires_in: int = 900) -> str:
    """Return a signed, short-lived URL for a file in a private bucket."""
    result = _client().storage.from_(BUCKET).create_signed_url(file_path, expires_in)
    return result.get("signedURL") or result.get("signedUrl", "")
