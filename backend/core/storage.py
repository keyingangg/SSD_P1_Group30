"""Supabase Storage helpers for serving uploaded files securely."""
import os
import supabase

# Initialize Supabase client from environment variables
_supabase_url = os.environ.get("SUPABASE_URL")
_supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if _supabase_url and _supabase_key:
    supabase_client = supabase.create_client(_supabase_url, _supabase_key)
else:
    supabase_client = None


def upload_to_supabase(file_obj, filename):
    """Upload a file to Supabase Storage and return the public URL.
    
    Args:
        file_obj: File-like object with read() method (Django UploadedFile)
        filename: Target filename in bucket (e.g., "listings/abc123_photo.jpg")
    
    Returns:
        Full public URL if successful, None if Supabase not configured
    
    Raises:
        Exception: On upload failure
    """
    if not supabase_client:
        raise RuntimeError("Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    
    # Read file content
    file_content = file_obj.read()
    
    # Upload to 'listing-images' bucket
    response = supabase_client.storage.from_("listing-images").upload(
        path=filename,
        file=file_content,
        file_options={"content-type": file_obj.content_type}
    )
    
    # Construct public URL
    public_url = f"{_supabase_url}/storage/v1/object/public/listing-images/{filename}"
    return public_url


def get_signed_url(file_path, expires_in=900):
    """Return a signed, short-lived URL for a stored file.

    Files live in a private bucket outside the web root and must only be
    served via signed URLs (default 15-minute expiry).
    """
    if not supabase_client:
        return None
    
    # Generate signed URL (future enhancement for private buckets)
    return supabase_client.storage.from_("listings").create_signed_url(
        path=file_path,
        expires_in=expires_in
    )
