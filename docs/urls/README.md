# Workflow URLs Documentation

## Base URLs Structure

### Main Redirect
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/` | `RedirectView` | `home` | Redirects to the Kanban board (`/kanban/`) |

### API Endpoints

#### Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/autosave-job/` | `edit_job_view_ajax.autosave_job_view` | `autosave_job_api` | Handles automatic saving of job data |
| `/api/get-job/` | `edit_job_view_ajax.get_job_api` | `get_job_api` | Retrieves job information |
| `/api/create-job/` | `edit_job_view_ajax.create_job_api` | `create_job_api` | Creates a new job |
| `/api/fetch_job_pricing/` | `edit_job_view_ajax.fetch_job_pricing_api` | `fetch_job_pricing_api` | Retrieves job pricing information |
| `/api/fetch_status_values/` | `edit_job_view_ajax.api_fetch_status_values` | `fetch_status_values` | Gets available job status values |

#### Timesheet Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/autosave-timesheet/` | `time_entry_view.autosave_timesheet_view` | `autosave_timesheet-api` | Handles automatic saving of timesheet entries |

#### Client Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/client-search/` | `client_view.ClientSearch` | `client_search_api` | Provides client search functionality |

#### System
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/get-env-variable/` | `server.get_env_variable` | `get_env_variable` | Retrieves environment variables |

#### Reports
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/reports/company-profit-loss/` | `CompanyProfitAndLossReport` | `api-company-profit-loss` | API endpoint for company profit and loss reports |

#### Xero Integration
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/xero/authenticate/` | `xero_view.xero_authenticate` | `api_xero_authenticate` | Initiates Xero authentication |
| `/api/xero/oauth/callback/` | `xero_view.xero_oauth_callback` | `oauth_callback_xero` | Handles Xero OAuth callback |
| `/api/xero/success/` | `xero_view.success_xero_connection` | `success_xero_connection` | Handles successful Xero connection |
| `/api/xero/refresh/` | `xero_view.refresh_xero_data` | `refresh_xero_data` | Refreshes Xero data |
| `/api/xero/contacts/` | `xero_view.get_xero_contacts` | `list_xero_contacts` | Retrieves Xero contacts |

### Client Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/clients/` | `client_view.ClientListView` | `list_clients` | Displays list of all clients |
| `/client/add/` | `client_view.AddClient` | `add_client` | Form to add new client |
| `/client/<uuid:pk>/` | `client_view.ClientUpdateView` | `update_client` | Updates existing client information |

### Invoice Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/invoices/` | `invoice_view.InvoiceListView` | `list_invoices` | Displays list of all invoices |
| `/invoices/<uuid:pk>` | `invoice_view.InvoiceUpdateView` | `update_invoice` | Updates existing invoice |

### Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/job/` | `edit_job_view_ajax.create_job_view` | `create_job` | Creates new job |
| `/job/<uuid:job_id>/` | `edit_job_view_ajax.edit_job_view_ajax` | `edit_job` | Edits existing job |
| `/jobs/<uuid:job_id>/update_status/` | `kanban_view.update_job_status` | `update_job_status` | Updates job status |

### Reports
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/reports/` | `ReportsIndexView` | `reports` | Main reports dashboard |
| `/reports/company-profit-loss/` | `CompanyProfitAndLossView` | `company-profit-loss-report` | Company profit and loss report view |

### Timesheet Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/timesheets/day/<str:date>/<uuid:staff_id>/` | `time_entry_view.TimesheetEntryView` | `timesheet_entry` | Timesheet entry for specific staff and date |
| `/timesheets/overview/` | `time_overview_view.TimesheetOverviewView` | `timesheet_overview` | Overview of all timesheets |
| `/timesheets/overview/<str:start_date>/` | `time_overview_view.TimesheetOverviewView` | `timesheet_overview_with_date` | Timesheet overview from specific date |
| `/timesheets/day/<str:date>/` | `time_overview_view.TimesheetDailyView` | `timesheet_daily_view` | View and edit timesheet entries for a specific day |

### Kanban Board
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/kanban/` | `kanban_view.kanban_view` | `view_kanban` | Main Kanban board view |
| `/kanban/fetch_jobs/<str:status>/` | `kanban_view.fetch_jobs` | `fetch_jobs` | Retrieves jobs filtered by status for Kanban board |

### Reports (continued)
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/reports/company-profit-and-loss/` | `CompanyProfitAndLossView` | `company_profit_and_loss_view` | Detailed company profit and loss report view |

### Authentication
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/login/` | `auth_views.LoginView` | `login` | User login page |
| `/logout/` | `auth_views.LogoutView` | `logout` | User logout handler |

### Staff Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/staff/<uuid:staff_id>/get_rates/` | `staff_view.get_staff_rates` | `get_staff_rates` | Retrieves rate information for specific staff member |

### Development Tools
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/__debug__/` | `debug_toolbar.urls` | N/A | Django Debug Toolbar (development only) |
