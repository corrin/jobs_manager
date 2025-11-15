# Orphan Objects Report - Data Integrity Checker

## Purpose

Scan every foreign key relationship in the database and report any broken references. Check business rules for fields that should not be null.

## Foreign Key Relationships

### Job App

#### Job Model
- `client` → Client (null=True, on_delete=SET_NULL)
- `contact` → ClientContact (null=True, on_delete=SET_NULL)
- `created_by` → Staff (null=True, on_delete=SET_NULL)
- `latest_estimate` → CostSet (OneToOne, null=True, on_delete=SET_NULL)
- `latest_quote` → CostSet (OneToOne, null=True, on_delete=SET_NULL)
- `latest_actual` → CostSet (OneToOne, null=True, on_delete=SET_NULL)
- `people` → Staff (ManyToMany)

#### CostSet Model
- `job` → Job (null=False, on_delete=CASCADE)

#### CostLine Model
- `cost_set` → CostSet (null=False, on_delete=CASCADE)

#### JobFile Model
- `job` → Job (null=False, on_delete=CASCADE)

#### JobEvent Model
- `job` → Job (null=True, on_delete=CASCADE)
- `staff` → Staff (null=True, on_delete=SET_NULL)

#### JobDeltaRejection Model
- `job` → Job (null=True, on_delete=SET_NULL)
- `staff` → Staff (null=True, on_delete=SET_NULL)

#### QuoteSpreadsheet Model
- `job` → Job (OneToOne, null=True, on_delete=CASCADE)

### Accounting App

#### Invoice Model
- `job` → Job (null=True, on_delete=CASCADE)
- `client` → Client (null=False, on_delete=CASCADE)

#### Bill Model
- `client` → Client (null=False, on_delete=CASCADE)

#### CreditNote Model
- `client` → Client (null=False, on_delete=CASCADE)

#### InvoiceLineItem Model
- `invoice` → Invoice (null=False, on_delete=CASCADE)
- `account` → XeroAccount (null=True, on_delete=SET_NULL)

#### BillLineItem Model
- `bill` → Bill (null=False, on_delete=CASCADE)
- `account` → XeroAccount (null=True, on_delete=SET_NULL)

#### CreditNoteLineItem Model
- `credit_note` → CreditNote (null=False, on_delete=CASCADE)
- `account` → XeroAccount (null=True, on_delete=SET_NULL)

#### Quote Model
- `job` → Job (OneToOne, null=True, on_delete=CASCADE)
- `client` → Client (null=False, on_delete=CASCADE)

### Workflow App

#### XeroJournalLineItem Model
- `journal` → XeroJournal (null=False, on_delete=CASCADE)
- `account` → XeroAccount (null=True, on_delete=SET_NULL)

#### AppError Model
- `resolved_by` → Staff (null=True, on_delete=SET_NULL)
- `job_id` (UUID field, not FK)
- `user_id` (UUID field, not FK)

### Client App

#### Client Model
- `merged_into` → Client (self-referential, null=True, on_delete=SET_NULL)

#### ClientContact Model
- `client` → Client (null=False, on_delete=CASCADE)

### Purchasing App

#### PurchaseOrder Model
- `supplier` → Client (null=True, on_delete=PROTECT)
- `job` → Job (null=True, on_delete=SET_NULL)

#### PurchaseOrderLine Model
- `purchase_order` → PurchaseOrder (null=False, on_delete=CASCADE)
- `job` → Job (null=True, on_delete=PROTECT)

#### PurchaseOrderSupplierQuote Model
- `purchase_order` → PurchaseOrder (OneToOne, null=False, on_delete=CASCADE)

#### Stock Model
- `job` → Job (null=True, on_delete=SET_NULL)
- `source_purchase_order_line` → PurchaseOrderLine (null=True, on_delete=SET_NULL)
- `source_parent_stock` → Stock (self-referential, null=True, on_delete=SET_NULL)
- `active_source_purchase_order_line_id` (UUID field, denormalized)

### Quoting App

#### SupplierProduct Model
- `supplier` → Client (null=False, on_delete=CASCADE)
- `price_list` → SupplierPriceList (null=False, on_delete=CASCADE)

#### SupplierPriceList Model
- `supplier` → Client (null=False, on_delete=CASCADE)

#### ScrapeJob Model
- `supplier` → Client (null=False, on_delete=CASCADE)

#### ProductParsingMapping Model
- `validated_by` → Staff (null=True, on_delete=SET_NULL)

## JSON Field References

### CostLine.meta
For kind='time':
- `staff_id` (UUID string) → Staff.id

### CostLine.ext_refs
- Stock IDs → Stock.id
- Purchase order line IDs → PurchaseOrderLine.id

### AppError
- `job_id` → Job.id
- `user_id` → Staff.id

## Business Rules

### Job Model
- `name` must not be null
- `job_number` must not be null (generated in Job.save())
- `status` must not be null
- `priority` must not be null (set in Job.save())
- `charge_out_rate` must not be null (set from CompanyDefaults in Job.save())
- `latest_estimate` must not be null (created in Job.save())
- `latest_quote` must not be null (created in Job.save())
- `latest_actual` must not be null (created in Job.save())

### CostSet Model
- `summary` must not be null (default factory)

### CostLine Model
- `accounting_date` must not be null
- For kind='time' AND cost_set.kind='actual': `meta.staff_id` must exist and reference valid Staff
- For kind='time' AND cost_set.kind='actual': `meta.is_billable` must be present
- Note: Estimates and quotes are projections of future work, not actual time tracking, so they don't require staff_id

### PurchaseOrder Model
- `supplier` must not be null
- `po_number` must not be null (generated in PurchaseOrder.save())
- `order_date` must not be null (default=timezone.now)

### Stock Model
- `date` must not be null (default=timezone.now)
- `active_source_purchase_order_line_id` computed in Stock.save() must match logic
- No circular references via `source_parent_stock`

### Client Model
- `additional_contact_persons` must not be null (default=list)
- `all_phones` must not be null (default=list)
- No circular merges via `merged_into`

### Staff Model
- `wage_rate` must not be null (default=0)
- `date_joined` must not be null (default=timezone.now)

### Invoice/Bill/CreditNote Models
- `status` must not be null (default=InvoiceStatus.DRAFT)

### JobFile Model
- For status="active": file must exist at `full_path/filename` on disk

### JobEvent Model
- `timestamp` must not be null (default=now)
- `event_type` must not be null (default="automatic_event")
- `schema_version` must not be null (default=0)

### ServiceAPIKey Model
- `key` must not be null (generated in ServiceAPIKey.save())

### AppError Model
- `severity` must not be null (default=logging.ERROR)

## API Response Structure

```json
{
  "scanned_at": "2025-11-16T12:34:56Z",
  "summary": {
    "total_fk_checks": 47,
    "total_business_rule_checks": 12,
    "total_issues": 42
  },
  "broken_fk_references": [
    {
      "model": "CostSet",
      "record_id": "uuid",
      "field": "job",
      "target_model": "Job",
      "target_id": "uuid"
    }
  ],
  "broken_json_references": [
    {
      "model": "CostLine",
      "record_id": "uuid",
      "field": "meta.staff_id",
      "staff_id": "uuid"
    }
  ],
  "business_rule_violations": [
    {
      "model": "CostLine",
      "record_id": "uuid",
      "field": "accounting_date",
      "rule": "must not be null"
    }
  ]
}
```

## on_delete Policy Review

Most `on_delete=CASCADE` relationships should be changed to `on_delete=PROTECT` to prevent accidental data loss.

### Keep CASCADE (parent-child hierarchies where child has no meaning without parent):
- CostSet.job → Job
- CostLine.cost_set → CostSet
- JobFile.job → Job
- JobEvent.job → Job
- InvoiceLineItem.invoice → Invoice
- BillLineItem.bill → Bill
- CreditNoteLineItem.credit_note → CreditNote
- XeroJournalLineItem.journal → XeroJournal
- ClientContact.client → Client
- PurchaseOrderLine.purchase_order → PurchaseOrder
- PurchaseOrderSupplierQuote.purchase_order → PurchaseOrder
- SupplierProduct.supplier → Client
- SupplierProduct.price_list → SupplierPriceList
- SupplierPriceList.supplier → Client
- ScrapeJob.supplier → Client

### Change to PROTECT (prevent accidental deletion of important records):
- Invoice.client → Client (currently CASCADE)
- Invoice.job → Job (currently CASCADE, should be PROTECT or SET_NULL)
- Bill.client → Client (currently CASCADE)
- CreditNote.client → Client (currently CASCADE)
- Quote.client → Client (currently CASCADE)
- Quote.job → Job (currently CASCADE, should be PROTECT or SET_NULL)
- QuoteSpreadsheet.job → Job (currently CASCADE, should be PROTECT or SET_NULL)

## Future Enhancements (Phase 2)

### Xero Sync Integrity
For records mastered in Xero (invoices, bills, clients, etc.), verify they still exist in Xero:
- Check Invoice.xero_id exists in Xero
- Check Bill.xero_id exists in Xero
- Check Client.xero_contact_id exists in Xero
- Check Stock.xero_id exists in Xero
- Flag records where Xero reports deleted/archived but we still have active records

Note: This requires Xero API calls and will be slower - separate endpoint recommended.

## Implementation

1. Service: `apps/job/services/data_integrity_service.py`
2. View: `apps/job/views/data_integrity_views.py`
3. Serializers: `apps/job/serializers/data_integrity_serializers.py`
4. URL: `/job/rest/data-integrity/scan/`
5. Migration: Change on_delete policies from CASCADE to PROTECT where appropriate
