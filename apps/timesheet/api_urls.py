"""
API URLs for timesheet endpoints.
Provides REST API routes for the Vue.js frontend.
"""

from django.urls import path

from .views.api import (
    DailyTimesheetAPIView,
    IMSWeeklyTimesheetAPIView,
    JobsAPIView,
    StaffListAPIView,
    WeeklyTimesheetAPIView,
)

app_name = "timesheet_api"

urlpatterns = [
    # Staff endpoints
    path("staff/", StaffListAPIView.as_view(), name="staff_list"),
    # Jobs endpoints
    path("jobs/", JobsAPIView.as_view(), name="jobs_list"),
    # Weekly timesheet (comprehensive, modern)
    path("weekly/", WeeklyTimesheetAPIView.as_view(), name="weekly_timesheet"),
    # Daily timesheet overview
    path("daily/", DailyTimesheetAPIView.as_view(), name="daily_overview"),
    path(
        "daily/<str:date>/",
        DailyTimesheetAPIView.as_view(),
        name="daily_overview_with_date",
    ),
    # Staff daily detail
    path(
        "staff/<uuid:staff_id>/daily/",
        DailyTimesheetAPIView.as_view(),
        name="staff_daily_detail",
    ),
]
