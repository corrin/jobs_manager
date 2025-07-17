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
from .views.api import JobsAPIView, StaffListAPIView, WeeklyTimesheetAPIView

app_name = "timesheet"

urlpatterns = [
    # ===== REST API ENDPOINTS (Modern - Vue.js Frontend) =====
    # Staff endpoints
    path("api/staff/", StaffListAPIView.as_view(), name="api_staff_list"),
    # Daily timesheet endpoints - using DailyTimesheetService (CostLine-based)
    path(
        "api/daily/", DailyTimesheetSummaryAPIView.as_view(), name="api_daily_summary"
    ),
    path(
        "api/daily/<str:target_date>/",
        DailyTimesheetSummaryAPIView.as_view(),
        name="api_daily_summary_with_date",
    ),
    path(
        "api/staff/<str:staff_id>/daily/",
        StaffDailyDetailAPIView.as_view(),
        name="api_staff_daily_detail",
    ),
    path(
        "api/staff/<str:staff_id>/daily/<str:target_date>/",
        StaffDailyDetailAPIView.as_view(),
        name="api_staff_daily_detail_with_date",
    ),
    # Weekly timesheet endpoints - using WeeklyTimesheetService (CostLine-based)
    path("api/weekly/", WeeklyTimesheetAPIView.as_view(), name="api_weekly_timesheet"),
    # Jobs endpoints
    path("api/jobs/", JobsAPIView.as_view(), name="api_jobs_list"),
]
