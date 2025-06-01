# API Endpoints Documentation

This document outlines key API endpoints within the `jobs_manager` project, primarily focusing on those exposed by the `workflow/api/` module.

## General Information

*   **Base URL:** `/api/` (relative to the Django application root)
*   **Authentication:** (Specify authentication methods, e.g., Session-based, Token-based, OAuth)
*   **Response Formats:** JSON

## Key Endpoints

### `workflow/api/xero/`

*   **Purpose:** Handles synchronization and interaction with the Xero accounting system.
*   **Files:**
    *   [`workflow/api/xero/sync.py`](workflow/api/xero/sync.py): Contains logic for syncing data between Django and Xero.
    *   [`workflow/api/xero/reprocess_xero.py`](workflow/api/xero/reprocess_xero.py): For reprocessing Xero-related data.
    *   [`workflow/api/xero/xero.py`](workflow/api/xero/xero.py): Core Xero API interaction.

### Example: Xero Synchronization

*   **Endpoint:** `/api/xero/sync/` (example, actual URL might vary)
*   **Method:** `POST`
*   **Description:** Initiates a synchronization process with Xero.
*   **Request Body (Example):**
    ```json
    {
        "data_type": "invoices",
        "start_date": "2023-01-01"
    }
    ```
*   **Response Body (Example):**
    ```json
    {
        "status": "success",
        "message": "Xero synchronization initiated."
    }
    ```

### Other Potential API Areas

*   **Client Management:** Endpoints for creating, retrieving, updating, and deleting client information.
*   **Job Management:** Endpoints for managing job details, status updates, etc.
*   **Timesheet Entries:** Endpoints for submitting and retrieving time entries.