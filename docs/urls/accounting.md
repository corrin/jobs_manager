# Accounting URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Quote Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/quote/<uuid:job_id>/pdf-preview/` | `submit_quote_view.generate_quote_pdf` | `accounting:generate_quote_pdf` | Generate a PDF quote summary for a specific job. |
| `/api/quote/<uuid:job_id>/send-email/` | `submit_quote_view.send_quote_email` | `accounting:send_quote_email` | Generate and prepare quote email with PDF attachment for a job. |

#### Reports
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/reports/calendar/` | `kpi_view.KPICalendarAPIView` | `accounting:api_kpi_calendar` | API Endpoint to provide KPI data for calendar display |

### Reports
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/reports/calendar/` | `kpi_view.KPICalendarTemplateView` | `accounting:kpi_calendar` | View for rendering the KPI Calendar page |
