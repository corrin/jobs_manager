# Timesheet URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Autosave Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/autosave/` | `api.autosave_timesheet_api` | `timesheet:api_autosave` | Auto-save timesheet entry data (API version of existing autosave functionality). |

#### Daily Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/daily/` | `daily_timesheet_views.daily_timesheet_summary` | `timesheet:api_daily_summary` | Get daily timesheet summary for all staff |
| `/api/daily/<str:target_date>/` | `daily_timesheet_views.daily_timesheet_summary` | `timesheet:api_daily_summary_with_date` | Get daily timesheet summary for all staff |

#### Entries Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/entries/` | `api.TimeEntriesAPIView` | `timesheet:api_time_entries` | API endpoint for timesheet entries CRUD operations. |
| `/api/entries/<uuid:entry_id>/` | `api.TimeEntriesAPIView` | `timesheet:api_time_entry_detail` | API endpoint for timesheet entries CRUD operations. |

#### Ims-Export Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/ims-export/` | `ims_export_view.IMSExportView` | `timesheet:api_ims_export` | API endpoint for IMS (Integrated Management System) export functionality. |

#### Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/jobs/` | `api.JobsAPIView` | `timesheet:api_jobs_list` | API endpoint to get available jobs for timesheet entries. |

#### Staff Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/staff/` | `api.StaffListAPIView` | `timesheet:api_staff_list` | API endpoint to get filtered list of staff members for timesheet operations. |
| `/api/staff/<str:staff_id>/daily/` | `daily_timesheet_views.staff_daily_detail` | `timesheet:api_staff_daily_detail` | Get detailed timesheet data for a specific staff member |
| `/api/staff/<str:staff_id>/daily/<str:target_date>/` | `daily_timesheet_views.staff_daily_detail` | `timesheet:api_staff_daily_detail_with_date` | Get detailed timesheet data for a specific staff member |

#### Weekly Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/weekly/` | `api.WeeklyTimesheetAPIView` | `timesheet:api_weekly_timesheet` | Comprehensive weekly timesheet API endpoint using WeeklyTimesheetService. |

### Autosave Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/autosave/` | `time_entry_view.autosave_timesheet_view` | `timesheet:autosave_timesheet` | Handles autosave requests for timesheet data. |

### Day Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/day/<str:date>/` | `time_overview_view.TimesheetDailyView` | `timesheet:timesheet_daily_view` | View for displaying daily timesheet data for all staff members. |
| `/day/<str:date>/<uuid:staff_id>/` | `time_entry_view.TimesheetEntryView` | `timesheet:timesheet_entry` | View to manage and display timesheet entries for a specific staff member and date. |

### Export_To_Ims Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/export_to_ims/` | `time_overview_view.TimesheetOverviewView` | `timesheet:timesheet_export_to_ims` | View for displaying timesheet overview including staff hours, job statistics and graphics. |

### Overview Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/overview/` | `time_overview_view.TimesheetOverviewView` | `timesheet:timesheet_overview` | View for displaying timesheet overview including staff hours, job statistics and graphics. |
| `/overview/<str:start_date>/` | `time_overview_view.TimesheetOverviewView` | `timesheet:timesheet_overview_with_date` | View for displaying timesheet overview including staff hours, job statistics and graphics. |

### Rest Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/rest/timesheet/entries/` | `modern_timesheet_views.ModernTimesheetEntryView` | `jobs:modern_timesheet_entry_rest` | Modern timesheet entry management using CostLine architecture |
| `/rest/timesheet/jobs/<uuid:job_id>/` | `modern_timesheet_views.ModernTimesheetJobView` | `jobs:modern_timesheet_job_rest` | Get timesheet entries for a specific job |
| `/rest/timesheet/staff/<uuid:staff_id>/date/<str:entry_date>/` | `modern_timesheet_views.ModernTimesheetDayView` | `jobs:modern_timesheet_day_rest` | Get timesheet entries for a specific day and staff |
