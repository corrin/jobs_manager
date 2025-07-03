# Job URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Company_Defaults Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/company_defaults/` | `edit_job_view_ajax.get_company_defaults_api` | `jobs:company_defaults_api` | API endpoint to fetch company default settings. |

#### Create-Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/create-job/` | `edit_job_view_ajax.create_job_api` | `jobs:create_job_api` | API endpoint to create a new job with default values. |

#### Fetch_Job_Pricing Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/fetch_job_pricing/` | `edit_job_view_ajax.fetch_job_pricing_api` | `jobs:fetch_job_pricing_api` | API endpoint to fetch job pricing data filtered by pricing methodology. |

#### Fetch_Status_Values Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/fetch_status_values/` | `edit_job_view_ajax.api_fetch_status_values` | `jobs:fetch_status_values` | API endpoint to fetch all available job status values. |

#### Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/autosave-job/` | `edit_job_view_ajax.autosave_job_view` | `jobs:autosave_job_api` | API endpoint for automatically saving job data during form editing. |
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
| `/api/jobs/<str:job_id>/update-status/` | `kanban_view_api.update_job_status` | `jobs:api_update_job_status` | Update job status - API endpoint. |
| `/api/jobs/<uuid:job_id>/quote-chat/` | `job_quote_chat_views.JobQuoteChatHistoryView` | `jobs:job_quote_chat_history` | REST view for getting and managing chat history for a job. |
| `/api/jobs/<uuid:job_id>/quote-chat/<str:message_id>/` | `job_quote_chat_views.JobQuoteChatMessageView` | `jobs:job_quote_chat_message` | REST view for updating individual chat messages. |
| `/api/jobs/<uuid:job_id>/reorder/` | `kanban_view_api.reorder_job` | `jobs:api_reorder_job` | Reorder job within or between columns - API endpoint. |
| `/api/jobs/advanced-search/` | `kanban_view_api.advanced_search` | `jobs:api_advanced_search` | Endpoint for advanced job search - API endpoint. |
| `/api/jobs/fetch-all/` | `kanban_view_api.fetch_all_jobs` | `jobs:api_fetch_all_jobs` | Fetch all jobs for Kanban board - API endpoint. |
| `/api/jobs/fetch-by-column/<str:column_id>/` | `kanban_view_api.fetch_jobs_by_column` | `jobs:api_fetch_jobs_by_column` | Fetch jobs by kanban column using new categorization system. |
| `/api/jobs/fetch/<str:status>/` | `kanban_view_api.fetch_jobs` | `jobs:api_fetch_jobs` | Fetch jobs by status with optional search - API endpoint. |
| `/api/jobs/status-values/` | `kanban_view_api.fetch_status_values` | `jobs:api_fetch_status_values` | Return available status values for Kanban - API endpoint. |

### Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/job/` | `edit_job_view_ajax.create_job_view` | `jobs:create_job` | Render the create job template page. |
| `/job/<uuid:job_id>/` | `edit_job_view_ajax.edit_job_view_ajax` | `jobs:edit_job` | Main view for editing jobs with comprehensive job data and pricing information. |
| `/job/<uuid:job_id>/workshop-pdf/` | `workshop_view.WorkshopPDFView` | `jobs:workshop-pdf` | API view for generating and serving workshop PDF documents for jobs. |
| `/job/archive-complete/` | `archive_completed_jobs_view.ArchiveCompleteJobsTemplateView` | `jobs:archive_complete_jobs` | View for rendering the related page. |

### Month-End Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/month-end/` | `job_management_view.month_end_view` | `jobs:month_end` | View for month-end processing of special jobs. |

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
| `/rest/jobs/<uuid:job_id>/quote/import/` | `<lambda>` | `jobs:quote_import_deprecated` | Lambda function endpoint |
| `/rest/jobs/<uuid:job_id>/quote/import/preview/` | `<lambda>` | `jobs:quote_import_preview_deprecated` | Lambda function endpoint |
| `/rest/jobs/<uuid:job_id>/quote/status/` | `quote_import_views.QuoteImportStatusView` | `jobs:quote_import_status` | Get current quote import status and latest quote information. |
| `/rest/jobs/<uuid:job_id>/time-entries/` | `job_rest_views.JobTimeEntryRestView` | `jobs:job_time_entries_rest` | REST view for Job time entries. |
| `/rest/jobs/<uuid:job_id>/workshop-pdf/` | `workshop_view.WorkshopPDFView` | `jobs:workshop-pdf` | API view for generating and serving workshop PDF documents for jobs. |
| `/rest/jobs/<uuid:pk>/cost_sets/<str:kind>/` | `job_costing_views.JobCostSetView` | `jobs:job_cost_set_rest` | Retrieve the latest CostSet for a specific job and kind. |
| `/rest/jobs/<uuid:pk>/quote/apply/` | `quote_sync_views.apply_quote` | `jobs:quote_apply` | Apply quote import from linked Google Sheet. |
| `/rest/jobs/<uuid:pk>/quote/link/` | `quote_sync_views.link_quote_sheet` | `jobs:quote_link_sheet` | Link a job to a Google Sheets quote template. |
| `/rest/jobs/<uuid:pk>/quote/preview/` | `quote_sync_views.preview_quote` | `jobs:quote_preview` | Preview quote import from linked Google Sheet. |
| `/rest/jobs/files/` | `job_file_view.JobFileView` | `jobs:job_file_base` | API view for managing job files including upload, download, update, and deletion. |
| `/rest/jobs/files/<int:file_path>/` | `job_file_view.JobFileView` | `jobs:job_file_delete` | API view for managing job files including upload, download, update, and deletion. |
| `/rest/jobs/files/<int:job_number>/` | `job_file_view.JobFileView` | `jobs:job_files_list` | API view for managing job files including upload, download, update, and deletion. |
| `/rest/jobs/files/<path:file_path>/` | `job_file_view.JobFileView` | `jobs:job_file_download` | API view for managing job files including upload, download, update, and deletion. |
| `/rest/jobs/files/<uuid:file_id>/thumbnail/` | `job_file_view.JobFileThumbnailView` | `jobs:job_file_thumbnail` | API view for serving JPEG thumbnails of job files. |
| `/rest/jobs/files/upload/` | `job_file_upload.JobFileUploadView` | `jobs:job_file_upload` | REST API view for uploading files to jobs. |
| `/rest/jobs/toggle-complex/` | `job_rest_views.JobToggleComplexRestView` | `jobs:job_toggle_complex_rest` | REST view for toggling Job complex mode. |
| `/rest/jobs/toggle-pricing-methodology/` | `job_rest_views.JobTogglePricingMethodologyRestView` | `jobs:job_toggle_pricing_methodology_rest` | DEPRECATED: This view is deprecated as pricing methodologies are not toggled. |
| `/rest/month-end/` | `month_end_rest_view.MonthEndRestView` | `jobs:month_end_rest` | REST API view for month-end processing of special jobs and stock data. |
| `/rest/timesheet/entries/` | `modern_timesheet_views.ModernTimesheetEntryView` | `jobs:modern_timesheet_entry_rest` | Modern timesheet entry management using CostLine architecture |
| `/rest/timesheet/jobs/<uuid:job_id>/` | `modern_timesheet_views.ModernTimesheetJobView` | `jobs:modern_timesheet_job_rest` | Get timesheet entries for a specific job |
| `/rest/timesheet/staff/<uuid:staff_id>/date/<str:entry_date>/` | `modern_timesheet_views.ModernTimesheetDayView` | `jobs:modern_timesheet_day_rest` | Get timesheet entries for a specific day and staff |
