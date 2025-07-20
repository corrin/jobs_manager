from django.urls import path

from apps.accounting.views import (
    JobAgingAPIView
)

from apps.accounting.views.kpi_view import (
    KPICalendarAPIView,
    KPICalendarTemplateView,
)
from apps.accounting.views.staff_performance_views import (
    StaffPerformanceDetailAPIView,
    StaffPerformanceSummaryAPIView,
    StaffPerformanceTemplateView,
)

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
        "api/reports/staff-performance-summary/",
        StaffPerformanceSummaryAPIView.as_view(),
        name="api_staff_performance_summary",
    ),
    path(
        "api/reports/staff-performance/<uuid:staff_id>/",
        StaffPerformanceDetailAPIView.as_view(),
        name="api_staff_performance_detail",
    ),
    path(
        "reports/calendar/",
        KPICalendarTemplateView.as_view(),
        name="kpi_calendar",
    ),
    path(
        "reports/staff-performance/",
        StaffPerformanceTemplateView.as_view(),
        name="staff_performance",
    ),
]
