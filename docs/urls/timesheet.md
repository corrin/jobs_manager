# Timesheet URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Daily Management

| URL Pattern                     | View                                                 | Name                                    | Description                               |
| ------------------------------- | ---------------------------------------------------- | --------------------------------------- | ----------------------------------------- |
| `/api/daily/`                   | `daily_timesheet_views.DailyTimesheetSummaryAPIView` | `timesheet:api_daily_summary`           | Get daily timesheet summary for all staff |
| `/api/daily/<str:target_date>/` | `daily_timesheet_views.DailyTimesheetSummaryAPIView` | `timesheet:api_daily_summary_with_date` | Get daily timesheet summary for all staff |

#### Jobs Management

| URL Pattern  | View              | Name                      | Description                                               |
| ------------ | ----------------- | ------------------------- | --------------------------------------------------------- |
| `/api/jobs/` | `api.JobsAPIView` | `timesheet:api_jobs_list` | API endpoint to get available jobs for timesheet entries. |

#### Staff Management

| URL Pattern                                          | View                                            | Name                                         | Description                                                                  |
| ---------------------------------------------------- | ----------------------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------- |
| `/api/staff/`                                        | `api.StaffListAPIView`                          | `timesheet:api_staff_list`                   | API endpoint to get filtered list of staff members for timesheet operations. |
| `/api/staff/<str:staff_id>/daily/`                   | `daily_timesheet_views.StaffDailyDetailAPIView` | `timesheet:api_staff_daily_detail`           | Get detailed timesheet data for a specific staff member                      |
| `/api/staff/<str:staff_id>/daily/<str:target_date>/` | `daily_timesheet_views.StaffDailyDetailAPIView` | `timesheet:api_staff_daily_detail_with_date` | Get detailed timesheet data for a specific staff member                      |

#### Weekly Management

| URL Pattern        | View                            | Name                             | Description                                                               |
| ------------------ | ------------------------------- | -------------------------------- | ------------------------------------------------------------------------- |
| `/api/weekly/`     | `api.WeeklyTimesheetAPIView`    | `timesheet:api_weekly_timesheet` | Comprehensive weekly timesheet API endpoint using WeeklyTimesheetService. |
| `/api/weekly/ims/` | `api.IMSWeeklyTimesheetAPIView` | `timesheet:weekly_timesheet_ims` | Weekly overview in IMS format (Tue-Fri plus following Mon).               |

### Rest Management

| URL Pattern                                                    | View                                              | Name                               | Description                                                   |
| -------------------------------------------------------------- | ------------------------------------------------- | ---------------------------------- | ------------------------------------------------------------- |
| `/rest/timesheet/entries/`                                     | `modern_timesheet_views.ModernTimesheetEntryView` | `jobs:modern_timesheet_entry_rest` | Modern timesheet entry management using CostLine architecture |
| `/rest/timesheet/jobs/<uuid:job_id>/`                          | `modern_timesheet_views.ModernTimesheetJobView`   | `jobs:modern_timesheet_job_rest`   | Get timesheet entries for a specific job                      |
| `/rest/timesheet/staff/<uuid:staff_id>/date/<str:entry_date>/` | `modern_timesheet_views.ModernTimesheetDayView`   | `jobs:modern_timesheet_day_rest`   | Get timesheet entries for a specific day and staff            |
