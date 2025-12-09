# Job URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Company_Defaults Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/company_defaults/` | `job_rest_views.get_company_defaults_api` | `jobs:company_defaults_api` | API endpoint to fetch company default settings. |

#### Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/job/<uuid:job_id>/assignment/` | `assign_job_view.AssignJobView` | `jobs:api_job_assigment` | API Endpoint for activities related to job assignment |
| `/api/job/completed/` | `archive_completed_jobs_view.ArchiveCompleteJobsListAPIView` | `jobs:api_jobs_completed` | API Endpoint to provide Job data for archiving display |
| `/api/job/completed/archive/` | `archive_completed_jobs_view.ArchiveCompleteJobsAPIView` | `jobs:api_jobs_archive` | API Endpoint to set 'paid' flag as True in the received jobs |

#### Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/jobs/<str:job_id>/update-status/` | `kanban_view_api.UpdateJobStatusAPIView` | `jobs:api_update_job_status` | Update job status - API endpoint. |
| `/api/jobs/<uuid:job_id>/quote-chat/` | `job_quote_chat_views.JobQuoteChatHistoryView` | `jobs:job_quote_chat_history` | REST view for getting and managing chat history for a job. |
| `/api/jobs/<uuid:job_id>/quote-chat/<str:message_id>/` | `job_quote_chat_views.JobQuoteChatMessageView` | `jobs:job_quote_chat_message` | REST view for updating individual chat messages. |
| `/api/jobs/<uuid:job_id>/quote-chat/interaction/` | `job_quote_chat_api.JobQuoteChatInteractionView` | `jobs:job_quote_chat_interaction` | API view to handle real-time interaction with the AI chat assistant. |
| `/api/jobs/<uuid:job_id>/reorder/` | `kanban_view_api.ReorderJobAPIView` | `jobs:api_reorder_job` | Reorder job within or between columns - API endpoint. |
| `/api/jobs/advanced-search/` | `kanban_view_api.AdvancedSearchAPIView` | `jobs:api_advanced_search` | Endpoint for advanced job search - API endpoint. |
| `/api/jobs/fetch-all/` | `kanban_view_api.FetchAllJobsAPIView` | `jobs:api_fetch_all_jobs` | Fetch all jobs for Kanban board - API endpoint. |
| `/api/jobs/fetch-by-column/<str:column_id>/` | `kanban_view_api.FetchJobsByColumnAPIView` | `jobs:api_fetch_jobs_by_column` | Fetch jobs by kanban column using new categorization system. |
| `/api/jobs/fetch/<str:status>/` | `kanban_view_api.FetchJobsAPIView` | `jobs:api_fetch_jobs` | Fetch jobs by status with optional search - API endpoint. |
| `/api/jobs/status-values/` | `kanban_view_api.FetchStatusValuesAPIView` | `jobs:api_fetch_status_values` | Return available status values for Kanban - API endpoint. |

#### Reports
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/reports/job-aging/` | `job_aging_view.JobAgingAPIView` | `accounting:api_job_aging` | API Endpoint to provide job aging data with financial and timing information |
| `/api/reports/job-movement/` | `JobMovementMetricsView` | `accounting:api_job_movement` | API endpoint for job movement and conversion metrics. |

### Job Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/job/<uuid:job_id>/workshop-pdf/` | `workshop_view.WorkshopPDFView` | `jobs:workshop-pdf` | API view for generating and serving workshop PDF documents for jobs. |
| `/job/archive-complete/` | `archive_completed_jobs_view.ArchiveCompleteJobsTemplateView` | `jobs:archive_complete_jobs` | View for rendering the related page. |

### Rest Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/rest/cost_lines/<str:cost_line_id>/` | `job_costline_views.CostLineUpdateView` | `jobs:costline_update_rest` | Update an existing CostLine |
| `/rest/cost_lines/<str:cost_line_id>/delete/` | `job_costline_views.CostLineDeleteView` | `jobs:costline_delete_rest` | Delete an existing CostLine |
| `/rest/data-integrity/scan/` | `data_integrity_views.DataIntegrityReportView` | `jobs:data_integrity_scan` | API view for comprehensive database integrity checking |
| `/rest/data-quality/archived-jobs-compliance/` | `data_quality_report_views.ArchivedJobsComplianceView` | `jobs:data_quality_archived_jobs_compliance` | API view for checking archived jobs compliance. |
| `/rest/jobs/` | `job_rest_views.JobCreateRestView` | `jobs:job_create_rest` | REST view for Job creation. |
| `/rest/jobs/<uuid:job_id>/` | `job_rest_views.JobDetailRestView` | `jobs:job_detail_rest` | REST view for CRUD operations on a specific Job. |
| `/rest/jobs/<uuid:job_id>/basic-info/` | `job_rest_views.JobBasicInformationRestView` | `jobs:job_basic_info_rest` | REST view for Job basic information. |
| `/rest/jobs/<uuid:job_id>/cost_sets/<str:kind>/cost_lines/` | `job_costline_views.CostLineCreateView` | `jobs:costline_create_any_rest` | Create a new CostLine in the specified job's CostSet |
| `/rest/jobs/<uuid:job_id>/cost_sets/actual/cost_lines/` | `job_costline_views.CostLineCreateView` | `jobs:costline_create_rest` | Create a new CostLine in the specified job's CostSet |
| `/rest/jobs/<uuid:job_id>/cost_sets/quote/revise/` | `job_costing_views.JobQuoteRevisionView` | `jobs:job_quote_revision_rest` | Manage quote revisions for jobs. |
| `/rest/jobs/<uuid:job_id>/costs/summary/` | `job_rest_views.JobCostSummaryRestView` | `jobs:job_cost_summary_rest` | REST view for Job cost summary. |
| `/rest/jobs/<uuid:job_id>/delivery-docket/` | `delivery_docket_view.DeliveryDocketView` | `jobs:delivery-docket` | API view for generating and serving delivery docket PDFs. |
| `/rest/jobs/<uuid:job_id>/delta-rejections/` | `job_rest_views.JobDeltaRejectionListRestView` | `jobs:job_delta_rejections_rest` | REST view that returns delta rejections for a specific job. |
| `/rest/jobs/<uuid:job_id>/events/` | `job_rest_views.JobEventListRestView` | `jobs:job_events_list_rest` | REST view for Job events list. |
| `/rest/jobs/<uuid:job_id>/events/create/` | `job_rest_views.JobEventRestView` | `jobs:job_events_rest` | REST view for Job events. |
| `/rest/jobs/<uuid:job_id>/files/` | `job_files_collection_view.JobFilesCollectionView` | `jobs:job_files_collection` | Collection operations on job files. |
| `/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/` | `job_file_detail_view.JobFileDetailView` | `jobs:job_file_detail` | Resource operations on individual job files. |
| `/rest/jobs/<uuid:job_id>/files/<uuid:file_id>/thumbnail/` | `job_file_thumbnail_view.JobFileThumbnailView` | `jobs:job_file_thumbnail` | Thumbnail serving for job files. |
| `/rest/jobs/<uuid:job_id>/header/` | `job_rest_views.JobHeaderRestView` | `jobs:job_header_rest` | REST view for Job header information. |
| `/rest/jobs/<uuid:job_id>/invoices/` | `job_rest_views.JobInvoicesRestView` | `jobs:job_invoices_rest` | REST view for Job invoices. |
| `/rest/jobs/<uuid:job_id>/jsa/` | `jsa_views.JobJSAListView` | `jobs:job_jsa_list` | List JSAs for a specific job. |
| `/rest/jobs/<uuid:job_id>/jsa/generate/` | `jsa_views.JobJSAGenerateView` | `jobs:job_jsa_generate` | Generate a new JSA for a specific job using AI. |
| `/rest/jobs/<uuid:job_id>/quote/` | `job_rest_views.JobQuoteRestView` | `jobs:job_quote_rest` | REST view for Job quotes. |
| `/rest/jobs/<uuid:job_id>/quote/accept/` | `job_rest_views.JobQuoteAcceptRestView` | `jobs:job_quote_accept_rest` | REST view for accepting job quotes. |
| `/rest/jobs/<uuid:job_id>/quote/import/` | `<lambda>` | `jobs:quote_import_deprecated` | Lambda function endpoint |
| `/rest/jobs/<uuid:job_id>/quote/import/preview/` | `<lambda>` | `jobs:quote_import_preview_deprecated` | Lambda function endpoint |
| `/rest/jobs/<uuid:job_id>/quote/status/` | `quote_import_views.QuoteImportStatusView` | `jobs:quote_import_status` | Get current quote import status and latest quote information. |
| `/rest/jobs/<uuid:job_id>/timeline/` | `job_rest_views.JobTimelineRestView` | `jobs:job_timeline_rest` | REST view for unified Job timeline. |
| `/rest/jobs/<uuid:job_id>/undo-change/` | `job_rest_views.JobUndoChangeRestView` | `jobs:job_undo_change_rest` | Undo a previously applied job delta. |
| `/rest/jobs/<uuid:job_id>/workshop-pdf/` | `workshop_view.WorkshopPDFView` | `jobs:workshop-pdf` | API view for generating and serving workshop PDF documents for jobs. |
| `/rest/jobs/<uuid:pk>/cost_sets/<str:kind>/` | `job_costing_views.JobCostSetView` | `jobs:job_cost_set_rest` | Retrieve the latest CostSet for a specific job and kind. |
| `/rest/jobs/<uuid:pk>/quote/apply/` | `quote_sync_views.ApplyQuoteAPIView` | `jobs:quote_apply` | Apply quote import from linked Google Sheet. |
| `/rest/jobs/<uuid:pk>/quote/link/` | `quote_sync_views.LinkQuoteSheetAPIView` | `jobs:quote_link_sheet` | Link a job to a Google Sheets quote template. |
| `/rest/jobs/<uuid:pk>/quote/preview/` | `quote_sync_views.PreviewQuoteAPIView` | `jobs:quote_preview` | Preview quote import from linked Google Sheet. |
| `/rest/jobs/delta-rejections/` | `job_rest_views.JobDeltaRejectionAdminRestView` | `jobs:job_delta_rejections_admin_rest` | Global listing of delta rejections for admin/monitoring usage. |
| `/rest/jobs/status-choices/` | `job_rest_views.JobStatusChoicesRestView` | `jobs:job_status_choices_rest` | REST view for Job status choices. |
| `/rest/jobs/weekly-metrics/` | `job_rest_views.WeeklyMetricsRestView` | `jobs:weekly_metrics_rest` | REST view for fetching weekly metrics. |
| `/rest/month-end/` | `month_end_rest_view.MonthEndRestView` | `jobs:month_end_rest` | REST API view for month-end processing of special jobs and stock data. |
| `/rest/safety-ai/generate-controls/` | `safety_document_views.SafetyAIGenerateControlsView` | `jobs:safety_ai_generate_controls` | Generate control measures for hazards using AI. |
| `/rest/safety-ai/generate-hazards/` | `safety_document_views.SafetyAIGenerateHazardsView` | `jobs:safety_ai_generate_hazards` | Generate hazards for a task using AI. |
| `/rest/safety-ai/improve-document/` | `safety_document_views.SafetyAIImproveDocumentView` | `jobs:safety_ai_improve_document` | Improve an entire safety document using AI. |
| `/rest/safety-ai/improve-section/` | `safety_document_views.SafetyAIImproveSectionView` | `jobs:safety_ai_improve_section` | Improve a section of a safety document using AI. |
| `/rest/safety-documents/` | `safety_document_views.SafetyDocumentListView` | `jobs:safety_documents_list` | List all safety documents (JSAs and SWPs). |
| `/rest/safety-documents/<uuid:doc_id>/` | `safety_document_views.SafetyDocumentDetailView` | `jobs:safety_document_detail` | Retrieve or delete a specific safety document. |
| `/rest/safety-documents/<uuid:doc_id>/content/` | `safety_document_views.SafetyDocumentContentView` | `jobs:safety_document_content` | Read or update content of a safety document's Google Doc. |
| `/rest/swp/` | `swp_views.SWPListView` | `jobs:swp_list` | List all SWPs (Safe Work Procedures). |
| `/rest/swp/generate/` | `swp_views.SWPGenerateView` | `jobs:swp_generate` | Generate a new SWP (Safe Work Procedure) using AI. |
| `/rest/timesheet/entries/` | `modern_timesheet_views.ModernTimesheetEntryView` | `jobs:modern_timesheet_entry_rest` | Modern timesheet entry management using CostLine architecture |
| `/rest/timesheet/jobs/<uuid:job_id>/` | `modern_timesheet_views.ModernTimesheetJobView` | `jobs:modern_timesheet_job_rest` | Get timesheet entries for a specific job |
| `/rest/timesheet/staff/<uuid:staff_id>/date/<str:entry_date>/` | `modern_timesheet_views.ModernTimesheetDayView` | `jobs:modern_timesheet_day_rest` | Get timesheet entries for a specific day and staff |
