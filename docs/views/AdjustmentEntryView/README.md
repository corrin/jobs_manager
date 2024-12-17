# Adjustment Entry Views Documentation

This document details the views related to handling adjustment entries in the workflow system.

## Overview

These views manage the creation and updating of adjustment entries, which are modifications to job pricing records.

## Views

### CreateAdjustmentEntryView

**Type**: Class-based View (CreateView)  
**Model**: AdjustmentEntry  
**Form**: AdjustmentEntryForm  
**Template**: `jobs/create_adjustment_entry.html`

#### Purpose
Handles the creation of new adjustment entries for job pricing records.

#### Attributes
- `model`: AdjustmentEntry
- `form_class`: AdjustmentEntryForm
- `template_name`: "jobs/create_adjustment_entry.html"

#### Methods

##### `form_valid(form: AdjustmentEntryForm) -> JsonResponse`
Processes valid form submission for creating an adjustment entry.

**Actions**:
1. Creates new adjustment entry without committing
2. Associates entry with specific job pricing
3. Saves the adjustment entry
4. Updates the associated job's last_updated timestamp
5. Returns response via parent class

##### `get_success_url()`
**Returns**: URL to job pricing update view for the associated job pricing

##### `form_invalid(form: AdjustmentEntryForm) -> JsonResponse`
Handles invalid form submission.
- Logs form errors at debug level
- Returns standard invalid form response

### UpdateAdjustmentEntryView

**Type**: Class-based View (UpdateView)  
**Model**: AdjustmentEntry  
**Form**: AdjustmentEntryForm  
**Template**: `workflow/update_adjustment_entry.html`

#### Purpose
Handles the updating of existing adjustment entries.

#### Attributes
- `model`: AdjustmentEntry
- `form_class`: AdjustmentEntryForm
- `template_name`: "workflow/update_adjustment_entry.html"

#### Methods

##### `form_valid(form: AdjustmentEntryForm) -> JsonResponse`
Processes valid form submission for updating an adjustment entry.

**Actions**:
1. Updates adjustment entry without committing
2. Saves the adjustment entry
3. Updates the associated job's last_updated timestamp
4. Returns response via parent class

##### `get_success_url()`
**Returns**: URL to job pricing update view for the associated job pricing

## Dependencies

- `logging`: For error logging
- `django.http.JsonResponse`: For JSON responses
- `django.shortcuts.get_object_or_404`: For object retrieval
- `django.urls.reverse_lazy`: For URL resolution
- `django.views.generic`: For class-based views
- `workflow.forms.AdjustmentEntryForm`: Form for adjustment entries
- `workflow.models.AdjustmentEntry`: Model for adjustment entries
- `workflow.models.JobPricing`: Model for job pricing

## Usage Notes

1. Both views require appropriate permissions to access
2. Forms handle both validation and saving of adjustment entries
3. After successful operations, users are redirected to the job pricing update view
4. Changes to adjustment entries trigger updates to the associated job's last_updated field
