"""Supabase Storage helpers for serving uploaded files securely."""


def get_signed_url(file_path, expires_in=900):
    """Return a signed, short-lived URL for a stored file.

    Files live in a private bucket outside the web root and must only be
    served via signed URLs (default 15-minute expiry).
    """
    # TODO: call Supabase Storage to generate a signed URL.
    pass
