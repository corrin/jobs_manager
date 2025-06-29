from rest_framework.pagination import PageNumberPagination


class FiftyPerPagePagination(PageNumberPagination):
    page_size = 50
