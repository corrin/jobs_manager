from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views, views_django_jobs

router = DefaultRouter()
router.register(
    r"api/django-jobs",
    views_django_jobs.DjangoJobViewSet,
    basename="django-job",
)
router.register(
    r"api/django-job-executions",
    views_django_jobs.DjangoJobExecutionViewSet,
    basename="django-job-execution",
)

urlpatterns = [
    path(
        "upload-supplier-pricing/",
        views.UploadSupplierPricingView.as_view(),
        name="upload_supplier_pricing",
    ),
    path(
        "api/extract-supplier-price-list/",
        views.extract_supplier_price_list_data_view,
        name="extract_supplier_price_list_data",
    ),
    path(
        "upload-price-list/",
        views.UploadPriceListView.as_view(),
        name="upload_price_list",
    ),
    # MCP API endpoints
    path(
        "api/mcp/search_stock/",
        views.search_stock_api,
        name="mcp_search_stock",
    ),
    path(
        "api/mcp/search_supplier_prices/",
        views.search_supplier_prices_api,
        name="mcp_search_supplier_prices",
    ),
    path(
        "api/mcp/job_context/<uuid:job_id>/",
        views.job_context_api,
        name="mcp_job_context",
    ),
] + router.urls
