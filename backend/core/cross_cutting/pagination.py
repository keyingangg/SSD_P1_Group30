"""Shared pagination classes."""
from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """Default page-number pagination (20 results per page)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
