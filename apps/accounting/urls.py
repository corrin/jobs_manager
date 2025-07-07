from django.urls import path

from apps.accounting.views import generate_quote_pdf, send_quote_email
from apps.accounting.views.kpi_view import KPICalendarAPIView, KPICalendarTemplateView
from apps.accounting.views.job_aging_view import JobAgingAPIView

app_name = "accounting"


urlpatterns = [
    path(
        "api/quote/<uuid:job_id>/pdf-preview/",
        generate_quote_pdf,
        name="generate_quote_pdf",
    ),
    path(
        "api/quote/<uuid:job_id>/send-email/",
        send_quote_email,
        name="send_quote_email",
    ),
    path(
        "api/reports/calendar/",
        KPICalendarAPIView.as_view(),
        name="api_kpi_calendar",
    ),
    path(
        "api/reports/job-aging/",
        JobAgingAPIView.as_view(),
        name="api_job_aging",
    ),
    path(
        "reports/calendar/",
        KPICalendarTemplateView.as_view(),
        name="kpi_calendar",
    ),
]
