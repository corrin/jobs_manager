# Debug Invoice Sync Views Documentation

## Overview

These views provide debugging functionality for synchronizing invoices with Xero. They include both an API endpoint for direct synchronization and a form-based interface for manual testing.

## Views

### debug_sync_invoice_view

**Type**: Function-based View

**Purpose**: Synchronizes a specific invoice with Xero for debugging purposes

**URL Pattern**: Accepts invoice number as URL parameter

### Parameters

- `request`: HttpRequest object
- `invoice_number`: String - The invoice number to sync

### Response Format

**Success Response** (200 OK):

```json
{
    "status": "success",
    "message": "Invoice {invoice_number} synced successfully."
}
```

**Error Response** (500 Internal Server Error):

```json
{
    "status": "error",
    "message": "Error message details"
}
```

### Implementation Details

```python
def debug_sync_invoice_view(request, invoice_number):
    try:
        single_sync_client(invoice_number=invoice_number, delete_local=True)
        return JsonResponse({
            "status": "success",
            "message": f"Invoice {invoice_number} synced successfully."
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
```

### Error Handling

- Catches all exceptions during sync process

- Returns 500 status code with error message

- Preserves original error message for debugging

### debug_sync_invoice_form

**Type**: Function-based View
**Template**: ```xero/debug_sync_invoice_form.html```
**Decorator**: ```@csrf_exempt```
**Purpose**: Provides a form interface for invoice synchronization testing

### Methods Supported

- GET: Displays the invoice sync form

- POST: Processes form submission and redirects

### Request Handling

#### GET Request

- Renders the debug sync invoice form template

- No additional context data required

#### POST Request

**Parameters**:

- ```invoice_number```: Form field containing invoice number

**Success Response** (200 OK):

**Validation** :

- Checks for presence of invoice_number
- Returns 400 Bad Request if missing

**Response Types** :

1. Missing Invoice Number (400 Bad Request):

```json
{
    "status": "error",
    "message": "Please provide an invoice number."
}

```

2. Successful Submission:
- Redirects to invoice list view with invoice number parameter
- Redirect URL format:
    
    `/invoices/?invoice_number={invoice_number}`

**Implementation Details**
```python
@csrf_exempt
def debug_sync_invoice_form(request):
    if request.method == "POST":
        invoice_number = request.POST.get("invoice_number")
        if not invoice_number:
            return JsonResponse({
                "status": "error",
                "message": "Please provide an invoice number."
            }, status=400)
        return redirect(f'{reverse("list_invoices")}?invoice_number={invoice_number}')
    return render(request, "xero/debug_sync_invoice_form.html")
```
