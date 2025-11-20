# Timesheet URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Daily Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/daily/<str:target_date>/` | `daily_timesheet_views.DailyTimesheetSummaryAPIView` | `timesheet:api_daily_summary` | Get daily timesheet summary for all staff |

#### Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/jobs/` | `api.JobsAPIView` | `timesheet:api_jobs_list` | API endpoint to get available jobs for timesheet entries. |

#### Payroll Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/payroll/pay-runs/` | `api.PayRunForWeekAPIView` | `timesheet:api_get_pay_run_for_week` | API endpoint to fetch pay run details for a specific week. |
| `/api/payroll/pay-runs/create/` | `api.CreatePayRunAPIView` | `timesheet:api_create_pay_run` | API endpoint to create a pay run in Xero Payroll. |
| `/api/payroll/pay-runs/refresh/` | `api.RefreshPayRunsAPIView` | `timesheet:api_refresh_pay_runs` | API endpoint to refresh cached pay runs from Xero. |
| `/api/payroll/post-staff-week/` | `api.PostWeekToXeroPayrollAPIView` | `timesheet:api_post_staff_week` | API endpoint to post a weekly timesheet to Xero Payroll. |

#### Staff Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/staff/` | `api.StaffListAPIView` | `timesheet:api_staff_list` | API endpoint to get filtered list of staff members for timesheet operations. |
| `/api/staff/<str:staff_id>/daily/<str:target_date>/` | `daily_timesheet_views.StaffDailyDetailAPIView` | `timesheet:api_staff_daily_detail` | Get detailed timesheet data for a specific staff member |

#### Weekly Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/weekly/` | `api.WeeklyTimesheetAPIView` | `timesheet:api_weekly_timesheet` | Comprehensive weekly timesheet API endpoint using WeeklyTimesheetService. |

### Rest Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/rest/timesheet/entries/` | `modern_timesheet_views.ModernTimesheetEntryView` | `jobs:modern_timesheet_entry_rest` | Modern timesheet entry management using CostLine architecture |
| `/rest/timesheet/jobs/<uuid:job_id>/` | `modern_timesheet_views.ModernTimesheetJobView` | `jobs:modern_timesheet_job_rest` | Get timesheet entries for a specific job |
| `/rest/timesheet/staff/<uuid:staff_id>/date/<str:entry_date>/` | `modern_timesheet_views.ModernTimesheetDayView` | `jobs:modern_timesheet_day_rest` | Get timesheet entries for a specific day and staff |
