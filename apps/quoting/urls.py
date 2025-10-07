from django.urls import path
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
        "api/extract-supplier-price-list/",
        views.extract_supplier_price_list_data_view,
        name="extract_supplier_price_list_data",
    ),
    path(
        "pdf-import/",
        views.PDFPriceListImportView.as_view(),
        name="pdf_price_list_import",
    ),
] + router.urls
