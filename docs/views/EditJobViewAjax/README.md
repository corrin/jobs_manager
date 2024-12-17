# View Documentation: Job Management APIs and Views

## Overview

These views provide features to job management, such as creating, retrieving, editing and autosaving jobs + APIs to fetch status and pricing data.

---

## View Specifications

### `create_job_view`

**Type**: Function-based View

**Template**: `jobs/create_job_and_redirect.html`

**Location**: `workflow/views/job_views.py`

### Description

Renders the template for creating a job and redirects to the appropriate workflow.

### Method

- **`GET`**: Renders the template.

---

### `api_fetch_status_values`

**Type**: Function-based API View

**Location**: `workflow/views/job_views.py`

### Description

Returns job status values as a JSON response.

### Method

- **`GET`**: Fetches the status values from `Job.JOB_STATUS_CHOICES`.

### Response

- **Success**: Returns a dictionary of status values.
- **Example**:

```json
{
    "1": "Pending",
    "2": "In Progress",
    "3": "Completed"
}

```

---

### `create_job_api`

**Type**: Function-based API View

**Location**: `workflow/views/job_views.py`

### Description

Creates a new job with default values and returns its ID in a JSON response.

### Method

- **`POST`**: Creates a job.

### Parameters

None (uses default values).

### Responses

- **Success**: Returns the job ID (`201`).
- **Error**: Returns an error message (`500`).

---

### `get_job_api`

**Type**: Function-based API View

**Location**: `workflow/views/job_views.py`

### Description

Fetches details of a job and its latest pricing information.

### Method

- **`GET`**: Retrieves job data.

### Parameters

- `job_id`: ID of the job to fetch.

### Responses

- **Success**: Returns job data including client name and latest pricing details.
- **Error**: Missing `job_id` (`400`), job not found (`404`), or unexpected error (`500`).

---

### `fetch_job_pricing_api`

**Type**: Function-based API View

**Location**: `workflow/views/job_views.py`

### Description

Fetches pricing data for a specific job based on the provided `pricing_type`.

### Method

- **`GET`**: Retrieves pricing data.

### Parameters

- `job_id`: ID of the job.
- `pricing_type`: Type of pricing data to retrieve.

### Responses

- **Success**: Returns a list of pricing data.
- **Error**: Missing parameters (`400`), no data found (`404`), or unexpected error (`500`).

---

### `edit_job_view_ajax`

**Type**: Function-based View

**Template**: `jobs/edit_job_ajax.html`

**Location**: `workflow/views/job_views.py`

### Description

Renders a template to edit a job, including its historical and latest pricing data.

### Method

- **`GET/POST`**: Fetches or submits job data.

### Context Variables

- `job`: Job instance.
- `company_defaults`: Company-level defaults.
- `historical_job_pricings_json`: Serialized historical pricings.
- `latest_job_pricings_json`: Serialized latest pricings.

---

### `autosave_job_view`

**Type**: Function-based API View

**Location**: `workflow/views/job_views.py`

### Description

Handles autosaving job data via a JSON payload.

### Method

- **`POST`**: Parses incoming JSON data and saves the job.

### Parameters

- JSON body with fields to update.

### Responses

- **Success**: Confirms successful autosave (`200`).
- **Error**: Validation errors (`400`), invalid JSON (`400`), or unexpected error (`500`).

---

## Common Utilities

### `form_to_dict`

**Type**: Helper Function

**Description**: Converts a Django form instance to a dictionary.

### Parameters

- `form`: Django form instance.

### Returns

- Dictionary with cleaned data if valid, else the initial data.

---

## Logging and Debugging

- **Logging**: Extensive use of the `logger` to debug and trace application flows, particularly in the `autosave_job_view` and `edit_job_view_ajax`.
- **Debugging Mode**: Controlled via the `DEBUG_JSON` toggle, enabling detailed logging of JSON serialization processes.