"""
Timesheet URLs - Single Source of Truth

Consolidated URL configuration for all timesheet functionality:
- Modern REST API endpoints using CostLine architecture
- Legacy HTML views for backward compatibility
- Clean, consistent URL structure
"""

from django.urls import path

from .api.daily_timesheet_views import daily_timesheet_summary, staff_daily_detail
from .views.api import JobsAPIView, StaffListAPIView, WeeklyTimesheetAPIView

app_name = "timesheet"

urlpatterns = [
    # ===== REST API ENDPOINTS (Modern - Vue.js Frontend) =====
    # Staff endpoints
    path("api/staff/", StaffListAPIView.as_view(), name="api_staff_list"),
    # Daily timesheet endpoints - using DailyTimesheetService (CostLine-based)
    path("api/daily/", daily_timesheet_summary, name="api_daily_summary"),
    path(
        "api/daily/<str:target_date>/",
        daily_timesheet_summary,
        name="api_daily_summary_with_date",
    ),
    path(
        "api/staff/<str:staff_id>/daily/",
        staff_daily_detail,
        name="api_staff_daily_detail",
    ),
    path(
        "api/staff/<str:staff_id>/daily/<str:target_date>/",
        staff_daily_detail,
        name="api_staff_daily_detail_with_date",
    ),
    # Weekly timesheet endpoints - using WeeklyTimesheetService (CostLine-based)
    path("api/weekly/", WeeklyTimesheetAPIView.as_view(), name="api_weekly_timesheet"),
    # Jobs endpoints
    path("api/jobs/", JobsAPIView.as_view(), name="api_jobs_list"),
]
