"""Supabase Storage helpers for secure upload and serving of uploaded files."""
import uuid

from django.conf import settings
from supabase import create_client

from core.validators import (
    scan_for_malware,
    validate_file_extension,
    validate_file_size,
    validate_mime_type,
)

_client = None


def _get_client():
    """Lazily build a Supabase client using the anon key.

    The service_role key bypasses all Row Level Security and must never be
    used in the application backend (NFSR-AZ-06). Writes/reads against the
    auction-images bucket are instead authorised by RLS policies on
    storage.objects scoped to that bucket for the anon role (see
    core/sql/storage_rls_policies.sql).
    """
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _client


def upload_image(file_obj, filename, max_bytes=None):
    """Validate and upload an image to the private bucket.

    The client-supplied filename is used only to determine the validated
    extension; the object is stored under a server-generated UUID v4 name so
    client input never reaches the storage path (NFSR-C-07 / NFSR-C-02).
    Returns the stored object key.
    """
    validate_file_size(file_obj, max_bytes=max_bytes)
    detected_mime = validate_mime_type(file_obj)
    ext = validate_file_extension(filename, detected_mime=detected_mime)
    scan_for_malware(file_obj)

    object_key = f"{uuid.uuid4()}{ext}"

    file_obj.seek(0)
    contents = file_obj.read()

    _get_client().storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        object_key,
        contents,
        {"content-type": detected_mime},
    )

    return object_key


def get_signed_url(file_path, expires_in=900):
    """Return a signed, short-lived URL for a stored file.

    Files live in a private bucket outside the web root and must only be
    served via signed URLs (default 15-minute expiry).
    """
    response = (
        _get_client()
        .storage.from_(settings.SUPABASE_STORAGE_BUCKET)
        .create_signed_url(file_path, expires_in)
    )
    return response["signedURL"]
