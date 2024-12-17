# Client Views Documentation

## Overview
This module contains views for managing client operations including listing, updating, searching, and adding clients. It includes integration with Xero for client synchronization.

## Authentication & Permissions

### Required Permissions
- `view_client`: Required for viewing client list and details
- `add_client`: Required for creating new clients 
- `change_client`: Required for updating existing clients
- `delete_client`: Required for removing clients

### Authentication
- All views require user authentication
- Unauthenticated requests are redirected to login page
- Session-based authentication is used

## Views

### ClientListView
**Type**: Class-based View (SingleTableView)  
**Model**: Client  
**Template**: `clients/list_clients.html`
**Required Permissions**: `view_client`

#### Purpose
Displays a paginated table of all clients in the system.

#### Attributes
- `model`: Client
- `template_name`: "clients/list_clients.html"

### ClientUpdateView
**Type**: Class-based View (UpdateView)  
**Model**: Client  
**Form**: ClientForm  
**Template**: `clients/update_client.html`
**Required Permissions**: `change_client`

#### Purpose
Handles updating existing client information.

#### Form Fields
- `name`: CharField (required, max_length=255)
  - Validation: Must be unique
- `email`: EmailField (optional)
  - Validation: Must be valid email format
- `phone`: CharField (optional, max_length=20)
  - Validation: Must match phone number format
- `address`: TextField (optional)

#### Example Request/Response

```http
POST /client/123/
Content-Type: application/x-www-form-urlencoded

name=Acme+Corp&email=contact@acme.com&phone=+1234567890&address=123+Business+St
```

- Success Response:

```http
HTTP/1.1 302 Found
Location: /clients/
```

- Error response:

```http
HTTP/1.1 200 OK
Content-Type: text/html

<form>
  ...
  <ul class="errorlist">
    <li>Name already exists</li>
  </ul>
  ...
</form>
```

### **ClientSearch**

**Type** : Function-based View

**Returns** : JsonResponse

**Required Permissions** :

`view_client`

### **Example Request/Response**

```clike
GET /api/client-search/?q=acme

```


Success Response:

```json
{
    "results": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Acme Corporation"
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "Acme Services Ltd"
        }
    ]
}

```

### **AddClient**

**Type** : Function-based View

**Required Permissions** :

`add_client`

### **Form Fields**

Same as ClientUpdateView

## **Xero Integration Details**

### **Synchronization Process**

1. **Initial Client Creation**
    - Local client record is created first
    - System attempts Xero synchronization
2. **Xero Sync Steps** ( )
    
    `sync_client_to_xero`
    
    - Creates/updates contact in Xero
    - Maps local client fields to Xero contact fields:
        
        ```python
        {
            'name': client.name,
            'emailAddress': client.email,
            'phones': [{'phoneNumber': client.phone}],
            'addresses': [{'addressLine1': client.address}]
        }
        
        ```
        
3. **Local Update** ( )
    
    `single_sync_client`
    
    - Fetches updated data from Xero
    - Updates local record with Xero contact ID
    - Synchronizes any additional Xero-specific fields

### **Error Handling**

- Network failures: Logged and reported to user
- Validation errors: Displayed in form
- Xero API limits: Handled with exponential backoff
- Duplicate contacts: Resolved through matching logic

### **Example Xero Sync Error Response**

```clike
HTTP/1.1 200 OK
Content-Type: text/html

<div class="error-message">
    Failed to sync with Xero: Rate limit exceeded.
    Pleasetry againin 60 seconds.
</div>

```

## **Form Validation Rules**

### **ClientForm**

1. **Name Field**
    - Required
    - Maximum length: 255 characters
    - Must be unique in system
    - Stripped of leading/trailing whitespace
2. **Email Field**
    - Optional
    - Must be valid email format
    - Maximum length: 254 characters
3. **Phone Field**
    - Optional
    - Validated against regex:
        
        `^\+?1?\d{9,15}$`
        
    - Stripped of spaces and special characters
4. **Address Field**
    - Optional
    - No maximum length
    - Newlines preserved

## **Usage Notes**

1. Client search requires minimum 3 characters
2. Xero integration is automatic on client creation
3. Failed Xero synchronization doesn't prevent client creation
4. Form validation maintains data on submission errors
5. All operations are logged for audit purposes

## **Error Handling**

1. **Form Validation Errors**
    - Displayed inline with fields
    - Form data preserved
    - Clear error messages provided
2. **Xero Integration Errors**
    - Logged with full stack trace
    - User-friendly message displayed
    - Option to retry synchronization
    - Admin notification for persistent failures
3. **Permission Errors**
    - Redirect to login if unauthenticated
    - 403 page for insufficient permissions
    - Logged for security monitoring