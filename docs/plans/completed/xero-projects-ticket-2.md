# Xero Projects Ticket 2: Invoice Model Refactoring - COMPLETED ✅

## Overview

Changing Invoice model relationship from OneToOneField to ForeignKey to support multiple invoices per job, as required by Xero Projects API.

## Progress

### ✅ All Tasks Completed

#### Task 2: Change Invoice.job from OneToOneField to ForeignKey ✅

- Changed: `models.OneToOneField(..., related_name="invoice", ...)`
- To: `models.ForeignKey(..., related_name="invoices", ...)`
- Impact: Changes `job.invoice` to `job.invoices.all()` throughout codebase

#### Task 3: Remove Job 'invoiced' property, add 'fully_invoiced' BooleanField ✅

- Removed existing `@property def invoiced()` completely
- Added `fully_invoiced = models.BooleanField(default=False)` field with helpful help_text
- This field is manually managed by Xero sync, not calculated

#### Task 4: Update all code using 'job.invoice' to use 'job.invoices' pattern ✅

- Updated `apps/job/services/paid_flag_service.py`:
  - Changed `job.invoice` → `job.invoices.all()`
  - Removed `RelatedObjectDoesNotExist` exception handling
  - Added logic to check all invoices are paid (handles multiple invoices per job)

#### Task 5: Update all code using 'job.invoiced' to use 'job.fully_invoiced' ✅

- Updated `apps/workflow/views/xero/xero_invoice_manager.py`:
  - Changed `job.invoiced` → `job.fully_invoiced` (property → field)

#### Task 6: Create and run migrations with data population ✅

- Created migration to add fully_invoiced field to Job model
- Created data migration to set fully_invoiced=True for jobs that have invoices
- Created migration to alter Invoice.job from OneToOneField to ForeignKey
- Applied all migrations successfully (updated 0 jobs - no existing invoices in dev DB)

#### Task 7: Test the changes ✅

- Django system check: PASSED
- Job model: fully_invoiced field works correctly (BooleanField, default=False)
- Job model: invoices relationship works correctly (ForeignKey, can have multiple)
- Invoice model: job relationship updated correctly (OneToOneField → ForeignKey)
- Confirmed old invoiced property removed (AttributeError as expected)
- PaidFlagService: Updated code using job.invoices works correctly
- XeroInvoiceManager: Updated code using job.fully_invoiced works correctly

## Implementation Notes

- **BREAKING CHANGES**: No backward compatibility
- Invoice.job: OneToOneField → ForeignKey (allows multiple invoices per job)
- Job.invoiced: property → fully_invoiced field (manually managed)
- All existing code must be updated to use new patterns
