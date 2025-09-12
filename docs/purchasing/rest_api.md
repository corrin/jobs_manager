# Purchasing REST API

This document describes the request and response formats for the REST endpoints provided by the `purchasing` app.

**Namespace**: `purchasing`

## Endpoints

### GET `/purchasing/rest/xero-items/`
Returns a list of items pulled from Xero.

**Response**
```json
[
  {"id": "<xero_item_id>", "code": "<item_code>", "name": "<item_name>"}
]
```

### GET `/purchasing/rest/purchase-orders/`
Returns a summary of purchase orders.

**Response**
```json
[
  {
    "id": "<uuid>",
    "po_number": "PO123",
    "status": "draft",
    "supplier": "<supplier_name>"
  }
]
```

### POST `/purchasing/rest/purchase-orders/`
Creates a purchase order with optional lines.

**Request**
```json
{
  "supplier_id": "<uuid>",
  "reference": "<ref>",
  "order_date": "YYYY-MM-DD",
  "expected_delivery": "YYYY-MM-DD",
  "lines": [
    {
      "job_id": "<uuid>",
      "description": "<text>",
      "quantity": 1,
      "unit_cost": 10.0,
      "price_tbc": false,
      "item_code": "ABC123"
    }
  ]
}
```

**Response** – `201 CREATED`
```json
{"id": "<uuid>", "po_number": "PO123"}
```

### PATCH `/purchasing/rest/purchase-orders/<uuid>/`
Updates basic fields or existing lines on a purchase order.

**Request**
```json
{
  "reference": "<new_ref>",
  "expected_delivery": "YYYY-MM-DD",
  "status": "ordered",
  "lines": [{"id": "<line_id>", "item_code": "NEW"}]
}
```

**Response**
```json
{"id": "<uuid>", "status": "ordered"}
```

### POST `/purchasing/rest/delivery-receipts/`
Processes a delivery receipt. The payload mirrors the old view logic.

**Request**
```json
{
  "purchase_order_id": "<uuid>",
  "allocations": {"<line_id>": 5}
}
```

**Response**
```json
{"success": true}
```

### GET `/purchasing/rest/stock/`
Lists active stock items.

**Response**
```json
[
  {"id": "<uuid>", "description": "Steel sheet", "quantity": 2.0, "unit_cost": 50.0}
]
```

### POST `/purchasing/rest/stock/<uuid>/consume/`
Consumes stock for a job.

**Request**
```json
{"job_id": "<uuid>", "quantity": 1.5}
```

**Response**
```json
{"success": true}
```
