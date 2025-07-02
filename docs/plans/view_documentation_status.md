# View Documentation Status

**Audit Date**: 2025-07-02  
**Total View Files**: 49  
**Documented Views**: 29  
**Undocumented Views**: 20  
**Coverage**: 59.2%

## Documentation Status by View File

### ACCOUNTING APP

#### apps/accounting/views/kpi_view.py
- **Status**: DOCUMENTED
- **Views**: KPICalendarTemplateView, KPICalendarAPIView
- **Documentation**: docs/views/KPIView/
- **Priority**: High (business analytics/reporting) - COMPLETED

#### apps/accounting/views/submit_quote_view.py  
- **Status**: DOCUMENTED
- **Views**: generate_quote_pdf, send_quote_email
- **Documentation**: docs/views/SubmitQuoteView/
- **Priority**: High (customer-facing quote submission) - COMPLETED

### ACCOUNTS APP

#### apps/accounts/views/password_views.py
- **Status**: NOT DOCUMENTED
- **Views**: SecurityPasswordChangeView
- **Priority**: Medium

#### apps/accounts/views/staff_api.py
- **Status**: NOT DOCUMENTED  
- **Views**: StaffListCreateAPIView, StaffRetrieveUpdateDestroyAPIView, update
- **Priority**: Medium

#### apps/accounts/views/staff_views.py
- **Status**: NOT DOCUMENTED
- **Views**: StaffListAPIView, StaffListView, StaffCreateView, StaffUpdateView, list, get_staff_rates
- **Priority**: Medium
- **Note**: Some documentation exists at docs/views/StaffView/ - NEEDS VERIFICATION

#### apps/accounts/views/token_view.py
- **Status**: NOT DOCUMENTED
- **Views**: CustomTokenObtainPairView, CustomTokenRefreshView, post, post
- **Priority**: Medium

#### apps/accounts/views/user_profile_view.py
- **Status**: NOT DOCUMENTED
- **Views**: get_current_user, logout_user
- **Priority**: Low

### CLIENT APP

#### apps/client/views/client_rest_views.py
- **Status**: DOCUMENTED
- **Views**: BaseClientRestView, ClientListAllRestView, ClientSearchRestView, ClientContactsRestView, ClientContactCreateRestView, ClientCreateRestView
- **Documentation**: docs/views/ClientRestView/
- **Priority**: High (core client management REST API) - COMPLETED

#### apps/client/views/client_views.py
- **Status**: PARTIALLY DOCUMENTED
- **Views**: ClientListView, ClientUpdateView, get_client_contact_persons, get_client_phones, get_all_clients_api, ClientSearch, client_detail, all_clients, AddClient, get_client_contacts_api, create_client_contact_api, client_contact_detail_api
- **Documentation**: docs/views/ClientView/ - NEEDS VERIFICATION of accuracy
- **Priority**: Medium (12 views - some may be covered by existing docs)

### JOB APP

#### apps/job/views/archive_completed_jobs_view.py
- **Status**: NOT DOCUMENTED
- **Views**: ArchiveCompleteJobsViews, ArchiveCompleteJobsTemplateView, ArchiveCompleteJobsListAPIView, ArchiveCompleteJobsAPIView, post
- **Priority**: Medium

#### apps/job/views/assign_job_view.py
- **Status**: NOT DOCUMENTED
- **Views**: AssignJobView, post, delete
- **Priority**: Medium

#### apps/job/views/edit_job_view_ajax.py
- **Status**: PARTIALLY DOCUMENTED
- **Views**: get_company_defaults_api, create_job_view, api_fetch_status_values, create_job_api, fetch_job_pricing_api, edit_job_view_ajax, autosave_job_view, process_month_end, add_job_event, toggle_complex_job, delete_job, create_linked_quote_api
- **Documentation**: docs/views/EditJobViewAjax/ - NEEDS VERIFICATION of accuracy
- **Priority**: High (12 views - core job editing functionality)

#### apps/job/views/job_costing_views.py
- **Status**: DOCUMENTED
- **Views**: JobCostSetView
- **Documentation**: docs/views/JobCostingView/
- **Priority**: HIGH (critical for project profitability tracking) - COMPLETED

#### apps/job/views/job_costline_views.py
- **Status**: DOCUMENTED
- **Views**: CostLineCreateView, CostLineUpdateView, CostLineDeleteView
- **Documentation**: docs/views/JobCostLineView/
- **Priority**: HIGH (detailed job costing and profitability tracking) - COMPLETED

#### apps/job/views/job_file_upload.py
- **Status**: NOT DOCUMENTED
- **Views**: JobFileUploadView, post
- **Priority**: Medium

#### apps/job/views/job_file_view.py
- **Status**: NOT DOCUMENTED
- **Views**: JobFileView, JobFileThumbnailView, post, get, put, delete, get
- **Priority**: Medium

#### apps/job/views/job_management_view.py
- **Status**: DOCUMENTED
- **Views**: month_end_view
- **Documentation**: docs/views/JobManagementView/
- **Priority**: HIGH (core workflow management) - COMPLETED

#### apps/job/views/job_quote_chat_views.py
- **Status**: NOT DOCUMENTED
- **Views**: BaseJobQuoteChatView, JobQuoteChatHistoryView, JobQuoteChatMessageView, dispatch, get, post, delete, patch
- **Priority**: Medium

#### apps/job/views/job_rest_views.py
- **Status**: DOCUMENTED
- **Views**: BaseJobRestView, JobCreateRestView, JobDetailRestView, JobToggleComplexRestView, JobTogglePricingMethodologyRestView, JobEventRestView, JobTimeEntryRestView, JobMaterialEntryRestView, JobAdjustmentEntryRestView
- **Documentation**: docs/views/JobRestView/
- **Priority**: HIGH (major REST API for core job lifecycle management) - COMPLETED

#### apps/job/views/kanban_view_api.py
- **Status**: PARTIALLY DOCUMENTED
- **Views**: fetch_all_jobs, update_job_status, reorder_job, fetch_jobs, fetch_status_values, advanced_search, fetch_jobs_by_column
- **Documentation**: docs/views/KanbanView/ - NEEDS VERIFICATION of accuracy
- **Priority**: High (7 views - some may be covered, others may be new)

#### apps/job/views/modern_timesheet_views.py
- **Status**: DOCUMENTED
- **Views**: ModernTimesheetEntryView, ModernTimesheetDayView, ModernTimesheetJobView
- **Documentation**: docs/views/ModernTimesheetView/
- **Priority**: HIGH (essential for time billing) - COMPLETED

#### apps/job/views/month_end_rest_view.py
- **Status**: NOT DOCUMENTED
- **Views**: MonthEndRestView, get, post
- **Priority**: Medium

#### apps/job/views/quote_import_views.py
- **Status**: DOCUMENTED
- **Views**: QuoteImportPreviewView, QuoteImportView, QuoteImportStatusView
- **Documentation**: docs/views/QuoteImportView/
- **Priority**: HIGH (external pricing data integration) - COMPLETED

#### apps/job/views/quote_sync_views.py
- **Status**: DOCUMENTED
- **Views**: link_quote_sheet, preview_quote, apply_quote
- **Documentation**: docs/views/QuoteImportView/ (combined documentation)
- **Priority**: HIGH (pricing and estimation workflow) - COMPLETED

#### apps/job/views/workshop_view.py
- **Status**: NOT DOCUMENTED
- **Views**: WorkshopPDFView, get
- **Priority**: Medium

### PURCHASING APP

#### apps/purchasing/views/delivery_receipt.py
- **Status**: NOT DOCUMENTED
- **Views**: DeliveryReceiptListView, DeliveryReceiptCreateView, post
- **Priority**: Medium

#### apps/purchasing/views/product_mapping.py
- **Status**: NOT DOCUMENTED
- **Views**: product_mapping_validation, validate_mapping
- **Priority**: Low

#### apps/purchasing/views/purchase_order.py
- **Status**: DOCUMENTED
- **Views**: PurchaseOrderListView, PurchaseOrderCreateView, PurchaseOrderEmailView, PurchaseOrderPDFView, autosave_purchase_order_view, delete_purchase_order_view, extract_supplier_quote_data_view
- **Documentation**: docs/views/PurchaseOrderView/
- **Priority**: HIGH (comprehensive purchase order lifecycle management) - COMPLETED

#### apps/purchasing/views/purchasing_rest_views.py
- **Status**: DOCUMENTED
- **Views**: XeroItemList, PurchaseOrderListCreateRestView, PurchaseOrderDetailRestView, DeliveryReceiptRestView, StockListRestView, StockDeactivateRestView, StockConsumeRestView
- **Documentation**: docs/views/PurchasingRestView/
- **Priority**: HIGH (inventory and cost management) - COMPLETED

#### apps/purchasing/views/stock.py
- **Status**: DOCUMENTED
- **Views**: use_stock_view, consume_stock_api_view, create_stock_api_view, search_available_stock_api, deactivate_stock_api_view
- **Documentation**: docs/views/StockView/
- **Priority**: HIGH (inventory management and material tracking) - COMPLETED

### QUOTING APP

#### apps/quoting/views.py
- **Status**: DOCUMENTED
- **Views**: index, UploadSupplierPricingView, UploadPriceListView, extract_supplier_price_list_data_view, search_stock_api, search_supplier_prices_api, job_context_api
- **Documentation**: docs/views/QuotingView/
- **Priority**: HIGH (supplier pricing and AI-powered quote generation) - COMPLETED

### TIMESHEET APP

#### apps/timesheet/views/api.py
- **Status**: DOCUMENTED
- **Views**: StaffListAPIView, TimeEntriesAPIView, JobsAPIView, WeeklyOverviewAPIView, DailyTimesheetAPIView, WeeklyTimesheetAPIView, autosave_timesheet_api
- **Documentation**: docs/views/TimesheetAPIView/
- **Priority**: HIGH (comprehensive timesheet API for labor tracking) - COMPLETED

#### apps/timesheet/views/ims_export_view.py
- **Status**: NOT DOCUMENTED
- **Views**: IMSExportView, get
- **Priority**: Low

#### apps/timesheet/views/time_entry_view.py
- **Status**: PARTIALLY DOCUMENTED
- **Views**: TimesheetEntryView, get, autosave_timesheet_view
- **Documentation**: docs/views/TimeEntryView/ - NEEDS VERIFICATION of accuracy
- **Priority**: Medium

#### apps/timesheet/views/time_overview_view.py
- **Status**: PARTIALLY DOCUMENTED
- **Views**: TimesheetOverviewView, TimesheetDailyView, get, post, load_paid_absence_form, submit_paid_absence, export_to_ims, get
- **Documentation**: docs/views/TimesheetOverviewView/ - NEEDS VERIFICATION of accuracy
- **Priority**: Medium

### WORKFLOW APP

#### apps/workflow/views/company_defaults_api.py
- **Status**: NOT DOCUMENTED
- **Views**: CompanyDefaultsAPIView, get, put, patch
- **Priority**: Medium

#### apps/workflow/views/xero/xero_view.py
- **Status**: DOCUMENTED
- **Views**: XeroIndexView, XeroErrorListAPIView, XeroErrorDetailAPIView, xero_authenticate, xero_oauth_callback, refresh_xero_token, success_xero_connection, refresh_xero_data, stream_xero_sync, create_xero_invoice, create_xero_purchase_order, create_xero_quote, delete_xero_invoice, delete_xero_quote, delete_xero_purchase_order, xero_disconnect, xero_sync_progress_page, get_xero_sync_info, start_xero_sync, trigger_xero_sync, xero_ping
- **Documentation**: docs/views/XeroView/ (comprehensive multi-file documentation)
- **Priority**: HIGH (critical Xero accounting integration with 22 views) - COMPLETED

## EXISTING DOCUMENTATION TO VERIFY

The following view documentation exists but needs verification against actual implementation:

1. **docs/views/AdjustmentEntryView/** - Need to find corresponding view file
2. **docs/views/ClientView/** - Corresponds to apps/client/views/client_views.py
3. **docs/views/DashboardView/** - Need to find corresponding view file  
4. **docs/views/DebugView/** - Need to find corresponding view file
5. **docs/views/EditJobViewAjax/** - Corresponds to apps/job/views/edit_job_view_ajax.py
6. **docs/views/InvoiceView/** - Need to find corresponding view file
7. **docs/views/KanbanView/** - Corresponds to apps/job/views/kanban_view_api.py
8. **docs/views/MaterialEntryView/** - Need to find corresponding view file
9. **docs/views/ReportView/** - Need to find corresponding view file
10. **docs/views/StaffView/** - Partially corresponds to apps/accounts/views/staff_views.py
11. **docs/views/TimeEntryView/** - Corresponds to apps/timesheet/views/time_entry_view.py
12. **docs/views/TimesheetOverviewView/** - Corresponds to apps/timesheet/views/time_overview_view.py
13. **docs/views/XeroView/** - Corresponds to apps/workflow/views/xero/xero_view.py

## NEXT STEPS

**Phase 2 Priority Order:**
1. Document 8 HIGH priority view files (core business functionality)
2. Verify accuracy of 6 existing documentation files that have corresponding views
3. Document remaining 28 view files
4. Find/remove documentation for views that no longer exist