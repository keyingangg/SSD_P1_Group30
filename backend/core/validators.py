"""File upload validators."""
import os

import clamd
import magic
from django.conf import settings
from rest_framework.exceptions import ValidationError

# Allowlist of permitted image types: MIME type -> permitted file extensions.
# Validating extension against the *detected* MIME (not the client-supplied
# one) prevents extension/content mismatches (e.g. a .php renamed to .jpg).
ALLOWED_MIME_TO_EXTENSIONS = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
    "image/gif": {".gif"},
}

ALLOWED_EXTENSIONS = frozenset().union(*ALLOWED_MIME_TO_EXTENSIONS.values())

DEFAULT_MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_mime_type(file_obj):
    """Verify a file's MIME type server-side using python-magic.

    Inspects the actual file bytes rather than trusting the client-supplied
    filename or Content-Type header. Returns the detected MIME type.
    """
    file_obj.seek(0)
    header = file_obj.read(2048)
    file_obj.seek(0)

    detected_mime = magic.from_buffer(header, mime=True)
    if detected_mime not in ALLOWED_MIME_TO_EXTENSIONS:
        raise ValidationError("Unsupported file type.")
    return detected_mime


def validate_file_extension(filename, detected_mime=None):
    """Reject disallowed/dangerous file extensions.

    Only extensions on the image allowlist are accepted, which also blocks
    dangerous extensions such as .bak, .swp, .env, .git, .php outright. When
    detected_mime is supplied, the extension must also match that MIME type.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("File extension not allowed.")

    if detected_mime is not None and ext not in ALLOWED_MIME_TO_EXTENSIONS[detected_mime]:
        raise ValidationError("File extension does not match file content.")

    return ext


def scan_for_malware(file_obj):
    """Scan uploaded file content for malware via a ClamAV daemon (NFSR-C-07).

    Fails closed: if the ClamAV daemon can't be reached at all (down,
    misconfigured, network issue), the upload is rejected rather than let
    through unscanned.
    """
    file_obj.seek(0)
    try:
        client = clamd.ClamdNetworkSocket(host=settings.CLAMD_HOST, port=settings.CLAMD_PORT)
        result = client.instream(file_obj)
    except Exception:
        raise ValidationError("File could not be scanned for malware. Please try again later.")
    finally:
        file_obj.seek(0)

    status, signature = result.get("stream", ("ERROR", None))
    if status == "FOUND":
        raise ValidationError("File failed malware scan.")
    if status != "OK":
        raise ValidationError("File could not be scanned for malware. Please try again later.")


def validate_file_size(file_obj, max_bytes=None):
    """Reject files exceeding the maximum permitted size."""
    max_bytes = max_bytes or DEFAULT_MAX_UPLOAD_BYTES

    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(0)

    if size > max_bytes:
        raise ValidationError("File exceeds the maximum permitted size.")
    return size
