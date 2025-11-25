 Here is Claude's plan:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Implement AlreadyLoggedException Pattern Globally

 Problem

 Multiple layers catch, log, and persist the same exception 4-5 times:
 - 35 files call persist_app_error()
 - ~15-20 code paths have nested handlers duplicating persistence
 - Scheduler jobs (3 files) don't persist at all - errors lost after log rotation

 Solution Architecture

 Create AlreadyLoggedException wrapper class in apps/workflow/exceptions.py:
 class AlreadyLoggedException(Exception):
     """Exception already persisted to database"""
     def __init__(self, original_exception, app_error_id=None):
         self.original = original_exception
         self.app_error_id = app_error_id
         super().__init__(str(original_exception))

 Pattern for all layers:
 try:
     # work
 except AlreadyLoggedException:
     raise  # Pass through, already persisted
 except Exception as exc:
     logger.error(f"Error: {exc}")
     app_error = persist_app_error(exc)
     raise AlreadyLoggedException(exc, app_error.id)

 Implementation Phases

 Phase 1: Foundation (Critical)
 1. Create AlreadyLoggedException class in apps/workflow/exceptions.py
 2. Update persist_app_error() to return AppError instance (currently returns None)
 3. Add scheduler jobs missing persistence (3 files):
   - apps/workflow/scheduler_jobs.py
   - apps/job/scheduler_jobs.py
   - apps/quoting/scheduler_jobs.py

 Phase 2: Integration Layer (High Priority)
 4. Strip all try/except from Xero integration (7 files in apps/workflow/api/xero/)
 - Keep input validation only
 - Let exceptions bubble naturally
 - Remove all persist_app_error() calls

 Phase 3: Service Layer (High Priority)
 5. Update service classes to check for AlreadyLoggedException:
 - apps/job/services/job_rest_service.py
 - apps/client/services/client_rest_service.py
 - apps/timesheet/services/payroll_sync.py
 - ~15 other service files

 Phase 4: View Layer (High Priority)
 6. Update all REST API views (40 files) to catch and wrap once
 7. Standardize BaseJobRestView.handle_service_error()

 Phase 5: Other Entry Points (Medium Priority)
 8. Update management commands (29 files)
 9. Update middleware error handlers

 Success Criteria

 - Single database AppError record per actual exception
 - Scheduler job errors persist (not lost to log rotation)
 - No duplicate persistence in nested handlers
 - All exception paths either persist OR re-raise AlreadyLoggedException

 Files Modified

 - ~100-120 files total
 - ~200-300 exception handlers updated
 - 1 new exception class
 - 1 modified helper function (persist_app_error)
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
