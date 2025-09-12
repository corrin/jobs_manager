# Accounting URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Reports
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/reports/calendar/` | `kpi_view.KPICalendarAPIView` | `accounting:api_kpi_calendar` | API Endpoint to provide KPI data for calendar display |
| `/api/reports/job-aging/` | `job_aging_view.JobAgingAPIView` | `accounting:api_job_aging` | API Endpoint to provide job aging data with financial and timing information |
| `/api/reports/staff-performance-summary/` | `staff_performance_views.StaffPerformanceSummaryAPIView` | `accounting:api_staff_performance_summary` | API endpoint for staff performance summary (all staff) |
| `/api/reports/staff-performance/<uuid:staff_id>/` | `staff_performance_views.StaffPerformanceDetailAPIView` | `accounting:api_staff_performance_detail` | API endpoint for individual staff performance detail |

### Reports
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/reports/calendar/` | `kpi_view.KPICalendarTemplateView` | `accounting:kpi_calendar` | View for rendering the KPI Calendar page |
| `/reports/staff-performance/` | `staff_performance_views.StaffPerformanceTemplateView` | `accounting:staff_performance` | View for rendering the Staff Performance page |
