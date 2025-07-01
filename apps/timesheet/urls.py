"""
Timesheet URLs - Single Source of Truth

Consolidated URL configuration for all timesheet functionality:
- Modern REST API endpoints using CostLine architecture
- Legacy HTML views for backward compatibility
- Clean, consistent URL structure
"""

from django.urls import path

from .api.daily_timesheet_views import daily_timesheet_summary, staff_daily_detail
from .views.api import (
    JobsAPIView,
    StaffListAPIView,
    TimeEntriesAPIView,
    WeeklyTimesheetAPIView,
    autosave_timesheet_api,
)
from .views.ims_export_view import IMSExportView
from .views.time_entry_view import TimesheetEntryView, autosave_timesheet_view
from .views.time_overview_view import TimesheetDailyView, TimesheetOverviewView

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
    # Time entries endpoints (Legacy support - will be phased out)
    path("api/entries/", TimeEntriesAPIView.as_view(), name="api_time_entries"),
    path(
        "api/entries/<uuid:entry_id>/",
        TimeEntriesAPIView.as_view(),
        name="api_time_entry_detail",
    ),
    # Jobs endpoints
    path("api/jobs/", JobsAPIView.as_view(), name="api_jobs_list"),
    # IMS Export
    path("api/ims-export/", IMSExportView.as_view(), name="api_ims_export"),
    # Autosave
    path("api/autosave/", autosave_timesheet_api, name="api_autosave"),
    # ===== HTML VIEWS (Legacy - Django Templates) =====
    # Weekly overview (HTML)
    path("overview/", TimesheetOverviewView.as_view(), name="timesheet_overview"),
    path(
        "overview/<str:start_date>/",
        TimesheetOverviewView.as_view(),
        name="timesheet_overview_with_date",
    ),
    # Daily overview (HTML)
    path("day/<str:date>/", TimesheetDailyView.as_view(), name="timesheet_daily_view"),
    # Individual timesheet entry (HTML)
    path(
        "day/<str:date>/<uuid:staff_id>/",
        TimesheetEntryView.as_view(),
        name="timesheet_entry",
    ),
    # Legacy autosave endpoint
    path("autosave/", autosave_timesheet_view, name="autosave_timesheet"),
    # IMS Export (HTML)
    path(
        "export_to_ims/",
        TimesheetOverviewView.as_view(),
        name="timesheet_export_to_ims",
    ),
]
