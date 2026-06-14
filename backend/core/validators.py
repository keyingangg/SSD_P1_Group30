"""File upload validators."""


def validate_mime_type(file_obj):
    """Verify a file's MIME type server-side using python-magic.

    Verification must be independent of client-supplied metadata.
    """
    # TODO: inspect file bytes with python-magic; allowlist permitted types.
    pass


def validate_file_extension(filename):
    """Reject disallowed/dangerous file extensions."""
    # TODO: block extensions such as .bak, .swp, .env, .git, .php.
    pass


def validate_file_size(file_obj, max_bytes=None):
    """Reject files exceeding the maximum permitted size."""
    # TODO: enforce a maximum upload size.
    pass
