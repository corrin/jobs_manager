# Generated URLs Documentation

## API Endpoints

#### Autosave Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/autosave/` | `api.autosave_timesheet_api` | `timesheet:api_autosave` | Auto-save timesheet entry data (API version of existing autosave functionality). |

#### Autosave-Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/autosave-job/` | `edit_job_view_ajax.autosave_job_view` | `jobs:autosave_job_api` | API endpoint for automatically saving job data during form editing. |

#### Client Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/client/<uuid:client_id>/contacts/` | `client_views.get_client_contacts_api` | `clients:api_get_client_contacts` | API endpoint to retrieve all contacts for a specific client. |
| `/api/client/contact/` | `client_views.create_client_contact_api` | `clients:api_create_client_contact` | API endpoint to create a new contact for a client. |
| `/api/client/contact/<uuid:contact_id>/` | `client_views.client_contact_detail_api` | `clients:api_client_contact_detail` | API endpoint to retrieve, update, or delete a specific contact. |

#### Company_Defaults Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/company_defaults/` | `edit_job_view_ajax.get_company_defaults_api` | `jobs:company_defaults_api` | API endpoint to fetch company default settings. |

#### Create-Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/create-job/` | `edit_job_view_ajax.create_job_api` | `jobs:create_job_api` | API endpoint to create a new job with default values. |

#### Daily Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/daily/` | `daily_timesheet_views.daily_timesheet_summary` | `timesheet:api_daily_summary` | Get daily timesheet summary for all staff |
| `/api/daily/<str:target_date>/` | `daily_timesheet_views.daily_timesheet_summary` | `timesheet:api_daily_summary_with_date` | Get daily timesheet summary for all staff |

#### Delivery-Receipts Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/delivery-receipts/process/` | `process_delivery_receipt` | `purchasing:delivery_receipts_process` | Process a delivery receipt for a purchase order based on detailed line allocations. |

#### Django-Job-Executions Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/django-job-executions/` | `views.dispatch` | `quoting:django-job-execution-list` | `.dispatch()` is pretty much the same as Django's regular dispatch, |
| `/api/django-job-executions/(?P<pk>[/.]+)/` | `views.dispatch` | `quoting:django-job-execution-detail` | `.dispatch()` is pretty much the same as Django's regular dispatch, |
| `/api/django-job-executions/(?P<pk>[/.]+)\.(?P<format>[a-z0-9]+)/?/` | `views.dispatch` | `quoting:django-job-execution-detail` | `.dispatch()` is pretty much the same as Django's regular dispatch, |

#### Django-Job-Executions\.(?P<Format>[A-Z0-9]+) Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/django-job-executions\.(?P<format>[a-z0-9]+)/?/` | `views.dispatch` | `quoting:django-job-execution-list` | `.dispatch()` is pretty much the same as Django's regular dispatch, |

#### Django-Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/django-jobs/` | `views.dispatch` | `quoting:django-job-list` | `.dispatch()` is pretty much the same as Django's regular dispatch, |
| `/api/django-jobs/(?P<pk>[/.]+)/` | `views.dispatch` | `quoting:django-job-detail` | `.dispatch()` is pretty much the same as Django's regular dispatch, |
| `/api/django-jobs/(?P<pk>[/.]+)\.(?P<format>[a-z0-9]+)/?/` | `views.dispatch` | `quoting:django-job-detail` | `.dispatch()` is pretty much the same as Django's regular dispatch, |

#### Django-Jobs\.(?P<Format>[A-Z0-9]+) Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/django-jobs\.(?P<format>[a-z0-9]+)/?/` | `views.dispatch` | `quoting:django-job-list` | `.dispatch()` is pretty much the same as Django's regular dispatch, |

#### Entries Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/entries/` | `api.TimeEntriesAPIView` | `timesheet:api_time_entries` | API endpoint for timesheet entries CRUD operations. |
| `/api/entries/<uuid:entry_id>/` | `api.TimeEntriesAPIView` | `timesheet:api_time_entry_detail` | API endpoint for timesheet entries CRUD operations. |

#### Extract-Supplier-Price-List Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/extract-supplier-price-list/` | `views.extract_supplier_price_list_data_view` | `quoting:extract_supplier_price_list_data` | Extract data from a supplier price list using Gemini. |

#### Fetch_Job_Pricing Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/fetch_job_pricing/` | `edit_job_view_ajax.fetch_job_pricing_api` | `jobs:fetch_job_pricing_api` | API endpoint to fetch job pricing data filtered by pricing methodology. |

#### Fetch_Status_Values Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/fetch_status_values/` | `edit_job_view_ajax.api_fetch_status_values` | `jobs:fetch_status_values` | API endpoint to fetch all available job status values. |

#### Ims-Export Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/ims-export/` | `ims_export_view.IMSExportView` | `timesheet:api_ims_export` | API endpoint for IMS (Integrated Management System) export functionality. |

#### Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/job/<uuid:job_id>/assignment/` | `assign_job_view.AssignJobView` | `jobs:api_job_assigment` | API Endpoint for activities related to job assignment |
| `/api/job/<uuid:job_id>/delete/` | `edit_job_view_ajax.delete_job` | `jobs:delete_job` | Deletes a job if it doesn't have any reality job pricing with actual data. |
| `/api/job/completed/` | `archive_completed_jobs_view.ArchiveCompleteJobsListAPIView` | `jobs:api_jobs_completed` | API Endpoint to provide Job data for archiving display |
| `/api/job/completed/archive/` | `archive_completed_jobs_view.ArchiveCompleteJobsAPIView` | `jobs:api_jobs_archive` | API Endpoint to set 'paid' flag as True in the received jobs |
| `/api/job/toggle-complex-job/` | `edit_job_view_ajax.toggle_complex_job` | `jobs:toggle_complex_job` | API endpoint to toggle the complex job mode for a specific job. |

#### Job-Event Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/job-event/<uuid:job_id>/add-event/` | `edit_job_view_ajax.add_job_event` | `jobs:add-event` | Create a new job event for a specific job. |

#### Job-Files Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/job-files/` | `job_file_view.JobFileView` | `jobs:job-files` | API view for managing job files including upload, download, update, and deletion. |
| `/api/job-files/<int:job_number>/` | `job_file_view.JobFileView` | `jobs:get-job-file` | API view for managing job files including upload, download, update, and deletion. |
| `/api/job-files/<path:file_path>/` | `job_file_view.JobFileView` | `jobs:serve-job-file` | API view for managing job files including upload, download, update, and deletion. |

#### Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/jobs/` | `api.JobsAPIView` | `timesheet:api_jobs_list` | API endpoint to get available jobs for timesheet entries. |
| `/api/jobs/<str:job_id>/update-status/` | `kanban_view_api.update_job_status` | `jobs:api_update_job_status` | Update job status - API endpoint. |
| `/api/jobs/<uuid:job_id>/quote-chat/` | `job_quote_chat_views.JobQuoteChatHistoryView` | `jobs:job_quote_chat_history` | REST view for getting and managing chat history for a job. |
| `/api/jobs/<uuid:job_id>/quote-chat/<str:message_id>/` | `job_quote_chat_views.JobQuoteChatMessageView` | `jobs:job_quote_chat_message` | REST view for updating individual chat messages. |
| `/api/jobs/<uuid:job_id>/reorder/` | `kanban_view_api.reorder_job` | `jobs:api_reorder_job` | Reorder job within or between columns - API endpoint. |
| `/api/jobs/advanced-search/` | `kanban_view_api.advanced_search` | `jobs:api_advanced_search` | Endpoint for advanced job search - API endpoint. |
| `/api/jobs/fetch-all/` | `kanban_view_api.fetch_all_jobs` | `jobs:api_fetch_all_jobs` | Fetch all jobs for Kanban board - API endpoint. |
| `/api/jobs/fetch-by-column/<str:column_id>/` | `kanban_view_api.fetch_jobs_by_column` | `jobs:api_fetch_jobs_by_column` | Fetch jobs by kanban column using new categorization system. |
| `/api/jobs/fetch/<str:status>/` | `kanban_view_api.fetch_jobs` | `jobs:api_fetch_jobs` | Fetch jobs by status with optional search - API endpoint. |
| `/api/jobs/status-values/` | `kanban_view_api.fetch_status_values` | `jobs:api_fetch_status_values` | Return available status values for Kanban - API endpoint. |

#### Product-Mapping Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/product-mapping/<uuid:mapping_id>/validate/` | `product_mapping.validate_mapping` | `purchasing:validate_mapping` | Validate a product parsing mapping. |

#### Purchase-Orders Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/purchase-orders/<uuid:purchase_order_id>/email/` | `purchase_order.PurchaseOrderEmailView` | `purchasing:purchase_orders_email` | API view for generating email links for purchase orders. |
| `/api/purchase-orders/<uuid:purchase_order_id>/pdf/` | `purchase_order.PurchaseOrderPDFView` | `purchasing:purchase_orders_pdf` | API view for generating and returning PDF documents for purchase orders. |
| `/api/purchase-orders/autosave/` | `purchase_order.autosave_purchase_order_view` | `purchasing:purchase_orders_autosave` | No description available |

#### Quote Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/quote/<uuid:job_id>/pdf-preview/` | `submit_quote_view.generate_quote_pdf` | `accounting:generate_quote_pdf` | Generate a PDF quote summary for a specific job. |
| `/api/quote/<uuid:job_id>/send-email/` | `submit_quote_view.send_quote_email` | `accounting:send_quote_email` | No description available |

#### Reports
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/reports/calendar/` | `kpi_view.KPICalendarAPIView` | `accounting:api_kpi_calendar` | API Endpoint to provide KPI data for calendar display |

#### Staff Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/staff/` | `staff_api.StaffListCreateAPIView` | `accounts:api_staff_list_create` | No description available |
| `/api/staff/` | `api.StaffListAPIView` | `timesheet:api_staff_list` | API endpoint to get list of staff members for timesheet. |
| `/api/staff/<str:staff_id>/daily/` | `daily_timesheet_views.staff_daily_detail` | `timesheet:api_staff_daily_detail` | Get detailed timesheet data for a specific staff member |
| `/api/staff/<str:staff_id>/daily/<str:target_date>/` | `daily_timesheet_views.staff_daily_detail` | `timesheet:api_staff_daily_detail_with_date` | Get detailed timesheet data for a specific staff member |
| `/api/staff/<uuid:pk>/` | `staff_api.StaffRetrieveUpdateDestroyAPIView` | `accounts:api_staff_detail` | No description available |
| `/api/staff/all/` | `staff_views.StaffListAPIView` | `accounts:api_staff_list` | No description available |
| `/api/staff/rates/<uuid:staff_id>/` | `staff_views.get_staff_rates` | `accounts:get_staff_rates` | No description available |

#### Stock Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/stock/<uuid:stock_id>/deactivate/` | `stock.deactivate_stock_api_view` | `purchasing:stock_deactivate_api` | API endpoint to deactivate a stock item (soft delete). |
| `/api/stock/consume/` | `stock.consume_stock_api_view` | `purchasing:stock_consume_api` | API endpoint to consume stock. |
| `/api/stock/create/` | `stock.create_stock_api_view` | `purchasing:stock_create_api` | API endpoint to create a new stock item. |
| `/api/stock/search/` | `stock.search_available_stock_api` | `purchasing:stock_search_api` | API endpoint to search available stock items for autocomplete. |

#### Supplier-Quotes Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/supplier-quotes/extract/` | `purchase_order.extract_supplier_quote_data_view` | `purchasing:supplier_quotes_extract` | Extract data from a supplier quote to pre-fill a PO form. |

#### System
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/company-defaults/` | `company_defaults_api.CompanyDefaultsAPIView` | `api_company_defaults` | API view for managing company default settings. |
| `/api/enums/<str:enum_name>/` | `get_enum_choices` | `get_enum_choices` | API endpoint to get enum choices. |
| `/api/mcp/job_context/<uuid:job_id>/` | `views.job_context_api` | `quoting:mcp_job_context` | MCP API endpoint for fetching job context (for "Interactive Quote" button). |
| `/api/mcp/search_stock/` | `views.search_stock_api` | `quoting:mcp_search_stock` | MCP API endpoint for searching internal stock inventory. |
| `/api/mcp/search_supplier_prices/` | `views.search_supplier_prices_api` | `quoting:mcp_search_supplier_prices` | MCP API endpoint for searching supplier pricing. |

#### Token Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/token/` | `token_view.CustomTokenObtainPairView` | `accounts:token_obtain_pair` | Customized token obtain view that handles password reset requirement |
| `/api/token/refresh/` | `token_view.CustomTokenRefreshView` | `accounts:token_refresh` | Customized token refresh view that uses httpOnly cookies |
| `/api/token/verify/` | `views.TokenVerifyView` | `accounts:token_verify` | Takes a token and indicates if it is valid.  This view provides no |

#### Weekly Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/weekly/` | `api.WeeklyTimesheetAPIView` | `timesheet:api_weekly_timesheet` | Comprehensive weekly timesheet API endpoint using WeeklyTimesheetService. |

#### Xero Integration
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/xero/authenticate/` | `xero_view.xero_authenticate` | `api_xero_authenticate` | Xero Authentication (Step 1: Redirect user to Xero OAuth2 login) |
| `/api/xero/create_invoice/<uuid:job_id>/` | `xero_view.create_xero_invoice` | `create_invoice` | Creates an Invoice in Xero for a given job. |
| `/api/xero/create_purchase_order/<uuid:purchase_order_id>/` | `xero_view.create_xero_purchase_order` | `create_xero_purchase_order` | Creates a Purchase Order in Xero for a given purchase order. |
| `/api/xero/create_quote/<uuid:job_id>/` | `xero_view.create_xero_quote` | `create_quote` | Creates a quote in Xero for a given job. |
| `/api/xero/delete_invoice/<uuid:job_id>/` | `xero_view.delete_xero_invoice` | `delete_invoice` | Deletes an invoice in Xero for a given job. |
| `/api/xero/delete_purchase_order/<uuid:purchase_order_id>/` | `xero_view.delete_xero_purchase_order` | `delete_xero_purchase_order` | Deletes a Purchase Order in Xero. |
| `/api/xero/delete_quote/<uuid:job_id>/` | `xero_view.delete_xero_quote` | `delete_quote` | Deletes a quote in Xero for a given job. |
| `/api/xero/disconnect/` | `xero_view.xero_disconnect` | `xero_disconnect` | Disconnects from Xero by clearing the token from cache and database. |
| `/api/xero/oauth/callback/` | `xero_view.xero_oauth_callback` | `xero_oauth_callback` | OAuth callback |
| `/api/xero/ping/` | `xero_view.xero_ping` | `xero_ping` | Simple endpoint to check if the user is authenticated with Xero. |
| `/api/xero/sync-info/` | `xero_view.get_xero_sync_info` | `xero_sync_info` | Get current sync status and last sync times, including Xero Items/Stock. |
| `/api/xero/sync-stream/` | `xero_view.stream_xero_sync` | `stream_xero_sync` | HTTP endpoint to serve an EventSource stream of Xero sync events. |
| `/api/xero/sync/` | `xero_view.start_xero_sync` | `synchronise_xero_data` | View function to start a Xero sync as a background task. |
| `/api/xero/webhook/` | `XeroWebhookView` | `xero_webhook` | Handle incoming Xero webhook notifications. |

### Add Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/add/` | `client_views.AddClient` | `clients:add_client` | No description available |

### All Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/all/` | `client_rest_views.ClientListAllRestView` | `clients:clients_rest:client_list_all_rest` | REST view for listing all clients. |

### Authentication
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/login/` | `base.RedirectView` | `backend-login-redirect` | Provide a redirect on any GET request. |
| `/login/` | `login` | `admin:login` | Display the login form for the given HttpRequest. |
| `/login/` | `views.LoginView` | `accounts:login` | Display the login form and handle the login action. |
| `/logout-session/` | `views.LogoutView` | `accounts:logout` | Log out the user and display the 'You are logged out' message. |
| `/logout/` | `logout` | `admin:logout` | Log out the user for the given HttpRequest. |
| `/logout/` | `user_profile_view.logout_user` | `accounts:api_logout` | Custom logout view that clears JWT httpOnly cookies |

### Autosave Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/autosave/` | `time_entry_view.autosave_timesheet_view` | `timesheet:autosave_timesheet` | Handles autosave requests for timesheet data. |

### Contacts Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/<uuid:client_id>/contacts/` | `client_rest_views.ClientContactsRestView` | `clients:clients_rest:client_contacts_rest` | REST view for fetching contacts of a client. |
| `/contacts/` | `client_rest_views.ClientContactCreateRestView` | `clients:clients_rest:client_contact_create_rest` | REST view for creating client contacts. |

### Create Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/create/` | `client_rest_views.ClientCreateRestView` | `clients:clients_rest:client_create_rest` | REST view for creating new clients. |

### Day Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/day/<str:date>/` | `time_overview_view.TimesheetDailyView` | `timesheet:timesheet_daily_view` | No description available |
| `/day/<str:date>/<uuid:staff_id>/` | `time_entry_view.TimesheetEntryView` | `timesheet:timesheet_entry` | View to manage and display timesheet entries for a specific staff member and date. |

### Delivery-Receipts Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/delivery-receipts/` | `delivery_receipt.DeliveryReceiptListView` | `purchasing:delivery_receipts_list` | View to list all purchase orders that can be received. |
| `/delivery-receipts/` | `purchasing_rest_views.DeliveryReceiptRestView` | `purchasing:delivery_receipts_rest` | No description available |
| `/delivery-receipts/<uuid:pk>/` | `delivery_receipt.DeliveryReceiptCreateView` | `purchasing:delivery_receipts_create` | View to create a delivery receipt for a purchase order. |

### Django Admin
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/(?P<app_label>django_apscheduler\|auth\|sites\|workflow\|accounts\|job\|purchasing)/` | `app_index` | `admin:app_list` | No description available |
| `/(?P<url>.*)/` | `catch_all_view` | `admin:N/A` | No description available |
| `/([/]+)/history/([/]+)/` | `history_form_view` | `admin:accounts_staff_simple_history` | No description available |
| `//` | `index` | `admin:index` | Display the main admin index page, which lists all of the installed |
| `//` | `changelist_view` | `admin:django_apscheduler_djangojob_changelist` | The 'change list' admin view for this model. |
| `//` | `changelist_view` | `admin:django_apscheduler_djangojobexecution_changelist` | The 'change list' admin view for this model. |
| `//` | `changelist_view` | `admin:auth_group_changelist` | The 'change list' admin view for this model. |
| `//` | `changelist_view` | `admin:sites_site_changelist` | The 'change list' admin view for this model. |
| `//` | `changelist_view` | `admin:workflow_companydefaults_changelist` | The 'change list' admin view for this model. |
| `//` | `changelist_view` | `admin:accounts_staff_changelist` | The 'change list' admin view for this model. |
| `//` | `changelist_view` | `admin:job_costset_changelist` | The 'change list' admin view for this model. |
| `//` | `changelist_view` | `admin:job_costline_changelist` | The 'change list' admin view for this model. |
| `//` | `changelist_view` | `admin:purchasing_purchaseorder_changelist` | The 'change list' admin view for this model. |
| `//` | `changelist_view` | `admin:purchasing_purchaseorderline_changelist` | The 'change list' admin view for this model. |
| `/<id>/password/` | `user_change_password` | `admin:auth_user_password_change` | No description available |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/` | `base.RedirectView` | `admin:N/A` | Provide a redirect on any GET request. |
| `/<path:object_id>/change/` | `change_view` | `admin:django_apscheduler_djangojob_change` | No description available |
| `/<path:object_id>/change/` | `change_view` | `admin:django_apscheduler_djangojobexecution_change` | No description available |
| `/<path:object_id>/change/` | `change_view` | `admin:auth_group_change` | No description available |
| `/<path:object_id>/change/` | `change_view` | `admin:sites_site_change` | No description available |
| `/<path:object_id>/change/` | `change_view` | `admin:workflow_companydefaults_change` | No description available |
| `/<path:object_id>/change/` | `change_view` | `admin:accounts_staff_change` | No description available |
| `/<path:object_id>/change/` | `change_view` | `admin:job_costset_change` | No description available |
| `/<path:object_id>/change/` | `change_view` | `admin:job_costline_change` | No description available |
| `/<path:object_id>/change/` | `change_view` | `admin:purchasing_purchaseorder_change` | No description available |
| `/<path:object_id>/change/` | `change_view` | `admin:purchasing_purchaseorderline_change` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:django_apscheduler_djangojob_delete` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:django_apscheduler_djangojobexecution_delete` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:auth_group_delete` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:sites_site_delete` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:workflow_companydefaults_delete` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:accounts_staff_delete` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:job_costset_delete` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:job_costline_delete` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:purchasing_purchaseorder_delete` | No description available |
| `/<path:object_id>/delete/` | `delete_view` | `admin:purchasing_purchaseorderline_delete` | No description available |
| `/<path:object_id>/history/` | `history_view` | `admin:django_apscheduler_djangojob_history` | The 'history' admin view for this model. |
| `/<path:object_id>/history/` | `history_view` | `admin:django_apscheduler_djangojobexecution_history` | The 'history' admin view for this model. |
| `/<path:object_id>/history/` | `history_view` | `admin:auth_group_history` | The 'history' admin view for this model. |
| `/<path:object_id>/history/` | `history_view` | `admin:sites_site_history` | The 'history' admin view for this model. |
| `/<path:object_id>/history/` | `history_view` | `admin:workflow_companydefaults_history` | The 'history' admin view for this model. |
| `/<path:object_id>/history/` | `history_view` | `admin:accounts_staff_history` | The 'history' admin view for this model. |
| `/<path:object_id>/history/` | `history_view` | `admin:job_costset_history` | The 'history' admin view for this model. |
| `/<path:object_id>/history/` | `history_view` | `admin:job_costline_history` | The 'history' admin view for this model. |
| `/<path:object_id>/history/` | `history_view` | `admin:purchasing_purchaseorder_history` | The 'history' admin view for this model. |
| `/<path:object_id>/history/` | `history_view` | `admin:purchasing_purchaseorderline_history` | The 'history' admin view for this model. |
| `/add/` | `add_view` | `admin:django_apscheduler_djangojob_add` | No description available |
| `/add/` | `add_view` | `admin:django_apscheduler_djangojobexecution_add` | No description available |
| `/add/` | `add_view` | `admin:auth_group_add` | No description available |
| `/add/` | `add_view` | `admin:sites_site_add` | No description available |
| `/add/` | `add_view` | `admin:workflow_companydefaults_add` | No description available |
| `/add/` | `add_view` | `admin:accounts_staff_add` | No description available |
| `/add/` | `add_view` | `admin:job_costset_add` | No description available |
| `/add/` | `add_view` | `admin:job_costline_add` | No description available |
| `/add/` | `add_view` | `admin:purchasing_purchaseorder_add` | No description available |
| `/add/` | `add_view` | `admin:purchasing_purchaseorderline_add` | No description available |
| `/autocomplete/` | `autocomplete_view` | `admin:autocomplete` | No description available |
| `/jsi18n/` | `i18n_javascript` | `admin:jsi18n` | Display the i18n JavaScript that the Django admin requires. |
| `/password_change/` | `password_change` | `admin:password_change` | Handle the "change password" task -- both form display and validation. |
| `/password_change/done/` | `password_change_done` | `admin:password_change_done` | Display the "success" page after a password change. |
| `/r/<path:content_type_id>/<path:object_id>/` | `views.shortcut` | `admin:view_on_site` | Redirect to an object's page based on a content-type ID and an object ID. |

### Export_To_Ims Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/export_to_ims/` | `time_overview_view.TimesheetOverviewView` | `timesheet:timesheet_export_to_ims` | View for displaying timesheet overview including staff hours, job statistics and graphics. |

### History_Refresh Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/history_refresh/` | `views.history_refresh` | `djdt:history_refresh` | Returns the refreshed list of table rows for the History Panel. |

### History_Sidebar Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/history_sidebar/` | `views.history_sidebar` | `djdt:history_sidebar` | Returns the selected debug toolbar history snapshot. |

### Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/job/` | `edit_job_view_ajax.create_job_view` | `jobs:create_job` | No description available |
| `/job/<uuid:job_id>/` | `edit_job_view_ajax.edit_job_view_ajax` | `jobs:edit_job` | No description available |
| `/job/<uuid:job_id>/workshop-pdf/` | `workshop_view.WorkshopPDFView` | `jobs:workshop-pdf` | No description available |
| `/job/archive-complete/` | `archive_completed_jobs_view.ArchiveCompleteJobsTemplateView` | `jobs:archive_complete_jobs` | View for rendering the related page. |

### Main Redirect
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `//` | `base.RedirectView` | `home` | Provide a redirect on any GET request. |

### Me Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/me/` | `user_profile_view.get_current_user` | `accounts:get_current_user` | Get current authenticated user information via JWT from httpOnly cookie |

### Media Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/media/(?P<path>.*)/` | `static.serve` | `N/A` | Serve static files below a given point in the directory structure. |

### Month-End Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/month-end/` | `job_management_view.month_end_view` | `jobs:month_end` | View for month-end processing of special jobs. |

### Other
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `//` | `APIRootView` | `quoting:api-root` | The default basic root view for DefaultRouter |
| `//` | `client_views.ClientListView` | `clients:list_clients` | No description available |
| `/<drf_format_suffix:format>/` | `APIRootView` | `quoting:api-root` | The default basic root view for DefaultRouter |
| `/<uuid:pk>/` | `client_views.ClientUpdateView` | `clients:update_client` | context_object_name = "clients" |

### Overview Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/overview/` | `time_overview_view.TimesheetOverviewView` | `timesheet:timesheet_overview` | View for displaying timesheet overview including staff hours, job statistics and graphics. |
| `/overview/<str:start_date>/` | `time_overview_view.TimesheetOverviewView` | `timesheet:timesheet_overview_with_date` | View for displaying timesheet overview including staff hours, job statistics and graphics. |

### Password_Change Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/password_change/` | `password_views.SecurityPasswordChangeView` | `accounts:password_change` | No description available |
| `/password_change/done/` | `views.PasswordChangeDoneView` | `accounts:password_change_done` | No description available |

### Password_Reset Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/password_reset/` | `views.PasswordResetView` | `accounts:password_reset` | No description available |
| `/password_reset/done/` | `views.PasswordResetDoneView` | `accounts:password_reset_done` | No description available |

### Product-Mapping Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/product-mapping/` | `product_mapping.product_mapping_validation` | `purchasing:product_mapping_validation` | Modern interface for validating product parsing mappings. |

### Purchase-Orders Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/purchase-orders/` | `purchase_order.PurchaseOrderListView` | `purchasing:purchase_orders_list` | View to list all purchase orders. |
| `/purchase-orders/` | `purchasing_rest_views.PurchaseOrderListCreateRestView` | `purchasing:purchase_orders_rest` | No description available |
| `/purchase-orders/<uuid:pk>/` | `purchase_order.PurchaseOrderCreateView` | `purchasing:purchase_orders_detail` | View to create or edit a purchase order, following the timesheet pattern. |
| `/purchase-orders/<uuid:pk>/` | `purchasing_rest_views.PurchaseOrderDetailRestView` | `purchasing:purchase_order_detail_rest` | Returns a full PO (including lines) |
| `/purchase-orders/<uuid:pk>/delete/` | `purchase_order.delete_purchase_order_view` | `purchasing:purchase_orders_delete` | No description available |
| `/purchase-orders/new/` | `purchase_order.PurchaseOrderCreateView` | `purchasing:purchase_orders_create` | View to create or edit a purchase order, following the timesheet pattern. |

### Render_Panel Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/render_panel/` | `views.render_panel` | `djdt:render_panel` | Render the contents of a panel |

### Reports
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/reports/calendar/` | `kpi_view.KPICalendarTemplateView` | `accounting:kpi_calendar` | View for rendering the KPI Calendar page |

### Reset Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/reset/<uidb64>/<token>/` | `views.PasswordResetConfirmView` | `accounts:password_reset_confirm` | No description available |
| `/reset/done/` | `views.PasswordResetCompleteView` | `accounts:password_reset_complete` | No description available |

### Rest Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/rest/cost_lines/<int:cost_line_id>/` | `job_costline_views.CostLineUpdateView` | `jobs:costline_update_rest` | Update an existing CostLine |
| `/rest/cost_lines/<int:cost_line_id>/delete/` | `job_costline_views.CostLineDeleteView` | `jobs:costline_delete_rest` | Delete an existing CostLine |
| `/rest/jobs/` | `job_rest_views.JobCreateRestView` | `jobs:job_create_rest` | REST view for Job creation. |
| `/rest/jobs/<uuid:job_id>/` | `job_rest_views.JobDetailRestView` | `jobs:job_detail_rest` | REST view for CRUD operations on a specific Job. |
| `/rest/jobs/<uuid:job_id>/adjustment-entries/` | `job_rest_views.JobAdjustmentEntryRestView` | `jobs:job_adjustment_entries_rest` | REST view for Job adjustment entries. |
| `/rest/jobs/<uuid:job_id>/cost_sets/<str:kind>/cost_lines/` | `job_costline_views.CostLineCreateView` | `jobs:costline_create_any_rest` | Create a new CostLine in the specified job's CostSet |
| `/rest/jobs/<uuid:job_id>/cost_sets/actual/cost_lines/` | `job_costline_views.CostLineCreateView` | `jobs:costline_create_rest` | Create a new CostLine in the specified job's CostSet |
| `/rest/jobs/<uuid:job_id>/events/` | `job_rest_views.JobEventRestView` | `jobs:job_events_rest` | REST view for Job events. |
| `/rest/jobs/<uuid:job_id>/material-entries/` | `job_rest_views.JobMaterialEntryRestView` | `jobs:job_material_entries_rest` | REST view for Job material entries. |
| `/rest/jobs/<uuid:job_id>/quote/import/` | `<lambda>` | `jobs:quote_import_deprecated` | No description available |
| `/rest/jobs/<uuid:job_id>/quote/import/preview/` | `<lambda>` | `jobs:quote_import_preview_deprecated` | Quote Import (DEPRECATED - file upload based) |
| `/rest/jobs/<uuid:job_id>/quote/status/` | `quote_import_views.QuoteImportStatusView` | `jobs:quote_import_status` | Get current quote import status and latest quote information. |
| `/rest/jobs/<uuid:job_id>/time-entries/` | `job_rest_views.JobTimeEntryRestView` | `jobs:job_time_entries_rest` | REST view for Job time entries. |
| `/rest/jobs/<uuid:job_id>/workshop-pdf/` | `workshop_view.WorkshopPDFView` | `jobs:workshop-pdf` | No description available |
| `/rest/jobs/<uuid:pk>/cost_sets/<str:kind>/` | `job_costing_views.JobCostSetView` | `jobs:job_cost_set_rest` | No description available |
| `/rest/jobs/<uuid:pk>/quote/apply/` | `quote_sync_views.apply_quote` | `jobs:quote_apply` | Apply quote import from linked Google Sheet. |
| `/rest/jobs/<uuid:pk>/quote/link/` | `quote_sync_views.link_quote_sheet` | `jobs:quote_link_sheet` | Link a job to a Google Sheets quote template. |
| `/rest/jobs/<uuid:pk>/quote/preview/` | `quote_sync_views.preview_quote` | `jobs:quote_preview` | Preview quote import from linked Google Sheet. |
| `/rest/jobs/files/` | `job_file_view.JobFileView` | `jobs:job_file_base` | API view for managing job files including upload, download, update, and deletion. |
| `/rest/jobs/files/<int:file_path>/` | `job_file_view.JobFileView` | `jobs:job_file_delete` | API view for managing job files including upload, download, update, and deletion. |
| `/rest/jobs/files/<int:job_number>/` | `job_file_view.JobFileView` | `jobs:job_files_list` | API view for managing job files including upload, download, update, and deletion. |
| `/rest/jobs/files/<path:file_path>/` | `job_file_view.JobFileView` | `jobs:job_file_download` | API view for managing job files including upload, download, update, and deletion. |
| `/rest/jobs/files/<uuid:file_id>/thumbnail/` | `job_file_view.JobFileThumbnailView` | `jobs:job_file_thumbnail` | No description available |
| `/rest/jobs/files/upload/` | `job_file_upload.JobFileUploadView` | `jobs:job_file_upload` | No description available |
| `/rest/jobs/toggle-complex/` | `job_rest_views.JobToggleComplexRestView` | `jobs:job_toggle_complex_rest` | REST view for toggling Job complex mode. |
| `/rest/jobs/toggle-pricing-methodology/` | `job_rest_views.JobTogglePricingMethodologyRestView` | `jobs:job_toggle_pricing_methodology_rest` | DEPRECATED: This view is deprecated as pricing methodologies are not toggled. |
| `/rest/month-end/` | `month_end_rest_view.MonthEndRestView` | `jobs:month_end_rest` | No description available |
| `/rest/timesheet/entries/` | `modern_timesheet_views.ModernTimesheetEntryView` | `jobs:modern_timesheet_entry_rest` | Modern timesheet entry management using CostLine architecture |
| `/rest/timesheet/jobs/<uuid:job_id>/` | `modern_timesheet_views.ModernTimesheetJobView` | `jobs:modern_timesheet_job_rest` | Get timesheet entries for a specific job |
| `/rest/timesheet/staff/<uuid:staff_id>/date/<str:entry_date>/` | `modern_timesheet_views.ModernTimesheetDayView` | `jobs:modern_timesheet_day_rest` | Get timesheet entries for a specific day and staff |

### Search Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/search/` | `client_rest_views.ClientSearchRestView` | `clients:clients_rest:client_search_rest` | REST view for client search. |

### Sql_Explain Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/sql_explain/` | `views.sql_explain` | `djdt:sql_explain` | Returns the output of the SQL EXPLAIN on the given query |

### Sql_Profile Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/sql_profile/` | `views.sql_profile` | `djdt:sql_profile` | Returns the output of running the SQL and getting the profiling statistics |

### Sql_Select Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/sql_select/` | `views.sql_select` | `djdt:sql_select` | Returns the output of the SQL SELECT statement |

### Staff Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/staff/` | `staff_views.StaffListView` | `accounts:list_staff` | No description available |
| `/staff/<uuid:pk>/` | `staff_views.StaffUpdateView` | `accounts:update_staff` | No description available |
| `/staff/new/` | `staff_views.StaffCreateView` | `accounts:create_staff` | No description available |

### Static Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/static/(?P<path>.*)/` | `static.serve` | `N/A` | Serve static files below a given point in the directory structure. |

### Stock Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/stock/` | `purchasing_rest_views.StockListRestView` | `purchasing:stock_list_rest` | No description available |
| `/stock/<uuid:stock_id>/` | `purchasing_rest_views.StockDeactivateRestView` | `purchasing:stock_deactivate_rest` | No description available |
| `/stock/<uuid:stock_id>/consume/` | `purchasing_rest_views.StockConsumeRestView` | `purchasing:stock_consume_rest` | No description available |

### System
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/xero-errors/` | `xero_view.XeroErrorListAPIView` | `xero-error-list` | API view for listing Xero synchronization errors. |
| `/xero-errors/<uuid:pk>/` | `xero_view.XeroErrorDetailAPIView` | `xero-error-detail` | API view for retrieving a single Xero synchronization error. |

### Template_Source Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/template_source/` | `views.template_source` | `djdt:template_source` | Return the source of a template, syntax-highlighted by Pygments if |

### Upload-Price-List Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/upload-price-list/` | `views.UploadPriceListView` | `quoting:upload_price_list` | No description available |

### Upload-Supplier-Pricing Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/upload-supplier-pricing/` | `views.UploadSupplierPricingView` | `quoting:upload_supplier_pricing` | No description available |

### Use-Stock Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/use-stock/` | `stock.use_stock_view` | `purchasing:use_stock` | View for the Use Stock page. |
| `/use-stock/<uuid:job_id>/` | `stock.use_stock_view` | `purchasing:use_stock_with_job` | View for the Use Stock page. |

### Xero Integration
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/xero/` | `xero_view.XeroIndexView` | `xero_index` | Note this page is currently inaccessible. We are using a dropdown menu instead. |
| `/xero/sync-progress/` | `xero_view.xero_sync_progress_page` | `xero_sync_progress` | Render the Xero sync progress page. |

### Xero-Items Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/xero-items/` | `purchasing_rest_views.XeroItemList` | `purchasing:xero_items_rest` | Return list of items from Xero. |
