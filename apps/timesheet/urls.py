"""
Timesheet URLs - Single Source of Truth

Consolidated URL configuration for all timesheet functionality:
- Modern REST API endpoints using CostLine architecture
- Legacy HTML views for backward compatibility
- Clean, consistent URL structure
"""

from django.urls import path

from .api.daily_timesheet_views import (
    DailyTimesheetSummaryAPIView,
    StaffDailyDetailAPIView,
)
from .views.api import (
    CreatePayRunAPIView,
    JobsAPIView,
    PayRunForWeekAPIView,
    PostWeekToXeroPayrollAPIView,
    RefreshPayRunsAPIView,
    StaffListAPIView,
    WeeklyTimesheetAPIView,
)

app_name = "timesheet"

urlpatterns = [
    # ===== REST API ENDPOINTS (Modern - Vue.js Frontend) =====
    # Staff endpoints
    path("api/staff/", StaffListAPIView.as_view(), name="api_staff_list"),
    # Daily timesheet endpoints - using DailyTimesheetService (CostLine-based)
    path(
        "api/daily/<str:target_date>/",
        DailyTimesheetSummaryAPIView.as_view(),
        name="api_daily_summary",
    ),
    path(
        "api/staff/<str:staff_id>/daily/<str:target_date>/",
        StaffDailyDetailAPIView.as_view(),
        name="api_staff_daily_detail",
    ),
    # Weekly timesheet endpoints - using WeeklyTimesheetService (CostLine-based)
    path("api/weekly/", WeeklyTimesheetAPIView.as_view(), name="api_weekly_timesheet"),
    # Jobs endpoints
    path("api/jobs/", JobsAPIView.as_view(), name="api_jobs_list"),
    # Xero Payroll endpoints
    path(
        "api/payroll/pay-runs/refresh",
        RefreshPayRunsAPIView.as_view(),
        name="api_refresh_pay_runs",
    ),
    path(
        "api/payroll/pay-runs/create",
        CreatePayRunAPIView.as_view(),
        name="api_create_pay_run",
    ),
    path(
        "api/payroll/pay-runs/",
        PayRunForWeekAPIView.as_view(),
        name="api_get_pay_run_for_week",
    ),
    path(
        "api/payroll/post-staff-week/",
        PostWeekToXeroPayrollAPIView.as_view(),
        name="api_post_staff_week",
    ),
]
