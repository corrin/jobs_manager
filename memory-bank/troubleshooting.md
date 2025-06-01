# Troubleshooting Guide

This document provides solutions and workarounds for common issues encountered during the development, deployment, or operation of the `jobs_manager` project.

## Common Issues and Solutions

### 1. Database Connection Errors

*   **Problem:** The application cannot connect to the MySQL database.
*   **Possible Causes:**
    *   Incorrect database credentials in Django settings.
    *   Database server is not running.
    *   Firewall blocking database port (default 3306).
    *   Incorrect `DATABASES` configuration in `jobs_manager/settings.py`.
*   **Solutions:**
    1.  Verify `DATABASES` settings in `jobs_manager/settings/base.py` (e.g., `NAME`, `USER`, `PASSWORD`, `HOST`, `PORT`).
    2.  Ensure the MySQL server is running.
    3.  Check firewall rules to allow connections to the database port.
    4.  Test database connectivity using a MySQL client from the application server.

### 2. Xero Synchronization Failures

*   **Problem:** Data synchronization with Xero is failing or incomplete.
*   **Possible Causes:**
    *   Expired Xero API token.
    *   Incorrect Xero API credentials or tenant ID.
    *   Network issues preventing communication with Xero.
    *   Data validation errors during sync (e.g., invalid invoice data).
*   **Solutions:**
    1.  Check the `workflow/models/xero_token.py` model and ensure the token is valid and not expired. Re-authenticate if necessary.
    2.  Review Xero API logs (if available) for specific error messages.
    3.  Inspect Django application logs for errors related to `workflow/api/xero/sync.py` or `workflow/services/xero_sync_service.py`.
    4.  Verify that the data being sent to Xero conforms to its API requirements.

### 3. Static Files Not Loading

*   **Problem:** CSS, JavaScript, or images are not loading correctly in the browser.
*   **Possible Causes:**
    *   `collectstatic` not run after changes to static files.
    *   Incorrect `STATIC_URL` or `STATIC_ROOT` settings in `jobs_manager/settings.py`.
    *   Web server (e.g., Nginx, Apache) not configured to serve static files.
*   **Solutions:**
    1.  Run `python manage.py collectstatic` to gather all static files into `STATIC_ROOT`.
    2.  Verify `STATIC_URL` and `STATIC_ROOT` in `jobs_manager/settings.py`.
    3.  Ensure your web server configuration correctly serves files from `STATIC_ROOT` at `STATIC_URL`.

## General Debugging Tips

*   **Check Logs:** Always start by reviewing application logs (e.g., `logs/` directory or console output) for error messages and stack traces.
*   **Django Debug Toolbar:** If enabled, use the Django Debug Toolbar for insights into database queries, templates, and request/response cycles.
*   **Browser Developer Tools:** Use your browser's developer console (F12) to check for network errors, JavaScript errors, and CSS issues.
*   **Reproduce the Issue:** Try to consistently reproduce the problem to narrow down the cause.
*   **Isolate the Problem:** Comment out sections of code or simplify configurations to identify the problematic component.