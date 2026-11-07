from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Pagination par numéro de page : ?page=2&page_size=50 (max. 100)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
