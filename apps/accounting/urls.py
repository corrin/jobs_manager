from django.urls import path


from apps.accounting.views.job_aging_view import JobAgingAPIView

app_name = "accounting"


urlpatterns = [
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
