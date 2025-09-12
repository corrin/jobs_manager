import logging
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from xero_python.accounting import AccountingApi
from xero_python.project.models import TimeEntryCreateOrUpdate

from apps.accounting.models import Bill, CreditNote, Invoice, Quote
from apps.accounts.models import Staff
from apps.client.models import Client
from apps.job.models.costing import CostLine
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Stock
from apps.workflow.api.xero.reprocess_xero import (
    set_client_fields,
    set_invoice_or_bill_fields,
    set_journal_fields,
)
from apps.workflow.api.xero.xero import (
    api_client,
    create_default_task,
    create_project,
    get_tenant_id,
    get_token,
    get_xero_items,
    update_project,
)
from apps.workflow.exceptions import XeroValidationError
from apps.workflow.models import CompanyDefaults, XeroAccount, XeroJournal
from apps.workflow.services.error_persistence import (
    persist_app_error,
    persist_xero_error,
)
from apps.workflow.services.validation import validate_required_fields
from apps.workflow.utils import get_machine_id

logger = logging.getLogger("xero")
SLEEP_TIME = 1  # Sleep after every API call to avoid hitting rate limits


def serialize_xero_object(obj):
    """Convert Xero objects to JSON-serializable format"""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, (list, tuple)):
        return [serialize_xero_object(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_xero_object(value) for key, value in obj.items()}
    elif hasattr(obj, "__dict__"):
        return serialize_xero_object(obj.__dict__)
    else:
        return str(obj)


def clean_json(data):
    """Remove Xero's internal fields and bulky repeated data"""
    if not isinstance(data, dict):
        return data

    exclude_keys = {
        "_currency_code",
        "_currency_rate",
        "_value2member_map_",
        "_generate_next_value_",
        "_member_names_",
        "__objclass__",
    }

    cleaned = {}
    for key, value in data.items():
        if key in exclude_keys or any(
            pattern in key
            for pattern in [
                "_value2member_map_",
                "_generate_next_value_",
                "_member_names_",
                "__objclass__",
            ]
        ):
            continue

        if isinstance(value, dict):
            cleaned[key] = clean_json(value)
        elif isinstance(value, list):
            cleaned[key] = [
                clean_json(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            cleaned[key] = value

    return cleaned


def process_xero_data(xero_obj):
    """Standard processing for all Xero objects"""
    return clean_json(serialize_xero_object(xero_obj))


def get_or_fetch_client(contact_id, reference=None):
    """Get client by Xero contact_id, fetching from API if needed"""
    client = Client.objects.filter(xero_contact_id=contact_id).first()
    if client:
        return client.get_final_client()

    response = AccountingApi(api_client).get_contacts(
        get_tenant_id(), i_ds=[contact_id], include_archived=True
    )
    time.sleep(SLEEP_TIME)

    if not response.contacts:
        raise ValueError(f"Client not found for {reference or contact_id}")

    synced = sync_clients([response.contacts[0]])
    if not synced:
        raise ValueError(f"Failed to sync client for {reference or contact_id}")

    return synced[0].get_final_client()


def sync_entities(items, model_class, xero_id_attr, transform_func):
    """Persist a batch of Xero objects.

    Args:
        items: Iterable of objects from Xero.
        model_class: Django model used for storage.
        xero_id_attr: Attribute name of the Xero ID on each item.
        transform_func: Callable converting an item to a model instance.

    Returns:
        int: Number of items successfully synced.
    """
    synced = 0
    for item in items:
        xero_id = getattr(item, xero_id_attr)

        # Skip deleted items that don't exist locally
        if getattr(item, "status", None) == "DELETED":
            if not model_class.objects.filter(xero_id=xero_id).exists():
                logger.info(
                    f"Skipping deleted {model_class.__name__} {xero_id} - doesn't exist locally"
                )
                continue

        instance = transform_func(item, xero_id)
        if instance:
            logger.info(
                f"Synced {model_class.__name__}: {getattr(instance, 'number', getattr(instance, 'name', xero_id))}"
            )
            synced += 1
    return synced


# Transform functions
def _extract_required_fields_xero(doc_type, xero_obj, xero_id):
    """Gather required values from a Xero document.

    Args:
        doc_type: Name of the document type.
        xero_obj: Object returned from Xero.
        xero_id: Identifier of the Xero object.

    Returns:
        Mapping of required field names to values.
    """
    # Map doc_type to field names
    match doc_type:
        case "invoice":
            number = getattr(xero_obj, "invoice_number", None)
        case "bill":
            number = getattr(xero_obj, "invoice_number", None)
        case "credit_note":
            number = getattr(xero_obj, "credit_note_number", None)
        case _:
            logger.error(f"Unknown document type for Xero sync: {doc_type}")
            return None
    client = get_or_fetch_client(xero_obj.contact.contact_id, number)
    date = getattr(xero_obj, "date", None)
    total_excl_tax = getattr(xero_obj, "sub_total", None)
    tax = getattr(xero_obj, "total_tax", None)
    total_incl_tax = getattr(xero_obj, "total", None)
    # Credit notes use remaining_credit instead of amount_due
    if doc_type == "credit_note":
        amount_due = getattr(xero_obj, "remaining_credit", None)
    else:
        amount_due = getattr(xero_obj, "amount_due", None)
    xero_last_modified = getattr(xero_obj, "updated_date_utc", None)
    raw_json = process_xero_data(xero_obj)

    required_fields = {
        "client": client,
        "date": date,
        "number": number,
        "total_excl_tax": total_excl_tax,
        "tax": tax,
        "total_incl_tax": total_incl_tax,
        "amount_due": amount_due,
        "xero_last_modified": xero_last_modified,
        "raw_json": raw_json,
    }
    validate_required_fields(required_fields, doc_type, xero_id)
    return required_fields


def transform_invoice(xero_invoice, xero_id):
    """Convert a Xero invoice into an Invoice instance.

    Args:
        xero_invoice: Invoice object from Xero.
        xero_id: Identifier of the invoice in Xero.

    Returns:
        The saved Invoice model.
    """
    fields = _extract_required_fields_xero("invoice", xero_invoice, xero_id)
    if not fields:
        return None
    invoice, created = Invoice.objects.get_or_create(xero_id=xero_id, defaults=fields)
    if not created:
        updated = False
        for key, value in fields.items():
            if getattr(invoice, key) != value:
                setattr(invoice, key, value)
                updated = True
        if updated:
            invoice.save()
    set_invoice_or_bill_fields(invoice, "INVOICE")
    if created:
        invoice.save()
    return invoice


def transform_bill(xero_bill, xero_id):
    """Convert a Xero bill into a Bill instance.

    Args:
        xero_bill: Bill object from Xero.
        xero_id: Identifier of the bill in Xero.

    Returns:
        The saved Bill model.
    """
    fields = _extract_required_fields_xero("bill", xero_bill, xero_id)
    if not fields:
        return None
    bill, created = Bill.objects.get_or_create(xero_id=xero_id, defaults=fields)
    if not created:
        updated = False
        for key, value in fields.items():
            if getattr(bill, key) != value:
                setattr(bill, key, value)
                updated = True
        if updated:
            bill.save()
    set_invoice_or_bill_fields(bill, "BILL")
    if created:
        bill.save()
    return bill


def transform_credit_note(xero_note, xero_id):
    """Convert a Xero credit note into a CreditNote instance.

    Args:
        xero_note: Credit note object from Xero.
        xero_id: Identifier of the credit note in Xero.

    Returns:
        The saved CreditNote model.
    """
    fields = _extract_required_fields_xero("credit_note", xero_note, xero_id)
    if not fields:
        return None
    note, created = CreditNote.objects.get_or_create(xero_id=xero_id, defaults=fields)
    if not created:
        updated = False
        for key, value in fields.items():
            if getattr(note, key) != value:
                setattr(note, key, value)
                updated = True
        if updated:
            note.save()
    set_invoice_or_bill_fields(note, "CREDIT_NOTE")
    if created:
        note.save()
    return note


def transform_journal(xero_journal, xero_id):
    """Convert a Xero journal into a XeroJournal instance.

    Args:
        xero_journal: Journal object from Xero.
        xero_id: Identifier of the journal in Xero.

    Returns:
        The saved XeroJournal model.
    """
    journal_date = getattr(xero_journal, "journal_date", None)
    created_date_utc = getattr(xero_journal, "created_date_utc", None)
    journal_number = getattr(xero_journal, "journal_number", None)
    raw_json = process_xero_data(xero_journal)
    validate_required_fields(
        {
            "journal_date": journal_date,
            "created_date_utc": created_date_utc,
            "journal_number": journal_number,
        },
        "journal",
        xero_id,
    )

    journal, created = XeroJournal.objects.get_or_create(
        xero_id=xero_id,
        defaults={
            "journal_date": journal_date,
            "created_date_utc": created_date_utc,
            "journal_number": journal_number,
            "raw_json": raw_json,
            # CREATED is correct! Xero journals are non-editable
            "xero_last_modified": created_date_utc,
        },
    )
    set_journal_fields(journal)
    if created:
        journal.save()
    return journal


def transform_stock(xero_item, xero_id):
    """Convert a Xero item into a Stock instance.

    Args:
        xero_item: Item object from Xero.
        xero_id: Identifier of the item in Xero.

    Returns:
        The saved Stock model.
    """
    # Get basic required fields - NO FALLBACKS, fail early if missing
    item_code = getattr(xero_item, "code", None)
    description = getattr(xero_item, "name", None)
    notes = getattr(xero_item, "description", None)
    is_tracked = getattr(xero_item, "is_tracked_as_inventory", None)
    xero_last_modified = getattr(xero_item, "updated_date_utc", None)
    raw_json = process_xero_data(xero_item)

    # Base validation requirements (always required)
    required_fields = {
        "code": item_code,
        "name": description,
        "is_tracked_as_inventory": is_tracked,
        "updated_date_utc": xero_last_modified,
    }

    # Only access and validate quantity_on_hand for tracked items
    if is_tracked:
        quantity = getattr(xero_item, "quantity_on_hand", None)
        required_fields["quantity_on_hand"] = quantity
        quantity_value = Decimal(str(quantity))
    else:
        # For untracked items, don't access quantity_on_hand at all
        quantity_value = Decimal("0")

    validate_required_fields(required_fields, "item", xero_id)

    defaults = {
        "item_code": item_code,
        "description": description,
        "notes": notes,
        "quantity": quantity_value,
        "raw_json": raw_json,
        "xero_last_modified": xero_last_modified,
        "xero_inventory_tracked": is_tracked,
    }
    # Handle missing sales_details.unit_price (set default if missing)
    if not xero_item.sales_details or xero_item.sales_details.unit_price is None:
        logger.warning(
            f"Item {xero_id}: Missing sales_details.unit_price, setting unit_revenue to 0"
        )
        defaults["unit_revenue"] = Decimal("0")
    else:
        defaults["unit_revenue"] = Decimal(str(xero_item.sales_details.unit_price))

    # Zero cost means we can supply it at no cost to us.
    if not xero_item.purchase_details or xero_item.purchase_details.unit_price is None:
        logger.warning(
            f"Item {xero_id}: Missing purchase_details.unit_price, setting unit_cost to 0"
        )
        defaults["unit_cost"] = Decimal("0")
    else:
        defaults["unit_cost"] = Decimal(str(xero_item.purchase_details.unit_price))

    stock, created = Stock.objects.get_or_create(xero_id=xero_id, defaults=defaults)
    updated = False
    for key, value in defaults.items():
        if getattr(stock, key, None) != value:
            setattr(stock, key, value)
            updated = True
    if updated:
        stock.save()
    return stock


def transform_quote(xero_quote, xero_id):
    """Convert a Xero quote into a Quote instance.

    Args:
        xero_quote: Quote object from Xero.
        xero_id: Identifier of the quote in Xero.

    Returns:
        The saved Quote model.
    """
    client = get_or_fetch_client(xero_quote.contact.contact_id, f"quote {xero_id}")
    raw_json = process_xero_data(xero_quote)

    status_data = raw_json.get("_status", {})
    status = status_data.get("_value_") if isinstance(status_data, dict) else None
    validate_required_fields({"status": status}, "quote", xero_id)

    quote, _ = Quote.objects.update_or_create(
        xero_id=xero_id,
        defaults={
            "client": client,
            "date": raw_json.get("_date"),
            "status": status,
            "total_excl_tax": Decimal(str(raw_json.get("_sub_total", 0))),
            "total_incl_tax": Decimal(str(raw_json.get("_total", 0))),
            "xero_last_modified": raw_json.get("_updated_date_utc"),
            "xero_last_synced": timezone.now(),
            "online_url": f"https://go.xero.com/app/quotes/edit/{xero_id}",
            "raw_json": raw_json,
        },
    )
    return quote


def transform_purchase_order(xero_po, xero_id):
    """Convert a Xero purchase order into a PurchaseOrder instance.

    Args:
        xero_po: Purchase order object from Xero.
        xero_id: Identifier of the purchase order in Xero.

    Returns:
        The saved PurchaseOrder model.
    """
    status_map = {
        "DRAFT": "draft",
        "SUBMITTED": "submitted",
        "AUTHORISED": "submitted",
        "BILLED": "fully_received",
        "VOIDED": "deleted",
    }
    supplier = get_or_fetch_client(
        xero_po.contact.contact_id, xero_po.purchase_order_number
    )

    po_number = getattr(xero_po, "purchase_order_number", None)
    order_date = getattr(xero_po, "date", None)
    status = getattr(xero_po, "status", None)
    xero_last_modified = getattr(xero_po, "updated_date_utc", None)
    raw_json = process_xero_data(xero_po)
    validate_required_fields(
        {
            "purchase_order_number": po_number,
            "date": order_date,
            "status": status,
        },
        "purchase_order",
        xero_id,
    )
    po, created = PurchaseOrder.objects.get_or_create(
        xero_id=xero_id,
        defaults={
            "supplier": supplier,
            "po_number": po_number,
            "order_date": order_date,
            "status": status_map.get(status, "draft"),
            "xero_last_modified": xero_last_modified,
            "raw_json": raw_json,
        },
    )
    po.po_number = po_number
    po.order_date = order_date
    po.expected_delivery = getattr(xero_po, "delivery_date", None)
    po.xero_last_modified = xero_last_modified
    po.xero_last_synced = timezone.now()
    po.status = status_map.get(status, "draft")
    po.save()
    if xero_po.line_items:
        for line in xero_po.line_items:
            description = getattr(line, "description", None)
            quantity = getattr(line, "quantity", None)
            if not description or quantity is None:
                error_msg = (
                    f"Missing required field for PurchaseOrderLine in PO {xero_id}"
                )
                logger.error(error_msg)
                persist_app_error(
                    ValueError(error_msg),
                    additional_context={
                        "xero_entity_type": "PurchaseOrder",
                        "xero_id": xero_id,
                        "po_number": po_number,
                        "sync_operation": "transform_line_items",
                        "missing_description": not description,
                        "missing_quantity": quantity is None,
                        "supplier_item_code": getattr(line, "item_code", None),
                    },
                )
                continue
            try:
                PurchaseOrderLine.objects.update_or_create(
                    purchase_order=po,
                    supplier_item_code=line.item_code or "",
                    description=description,
                    defaults={
                        "quantity": quantity,
                        "unit_cost": getattr(line, "unit_amount", None),
                    },
                )
            except PurchaseOrderLine.MultipleObjectsReturned as exc:
                logger.error(
                    f"Multiple PurchaseOrderLine records found for document '{po_number}' "
                    f"(Xero ID: {xero_id}), line item: '{description}', "
                    f"supplier_item_code: '{line.item_code or ''}'"
                )
                persist_app_error(
                    exc,
                    additional_context={
                        "xero_entity_type": "PurchaseOrder",
                        "xero_id": xero_id,
                        "po_number": po_number,
                        "sync_operation": "create_line_items",
                        "description": description,
                        "supplier_item_code": line.item_code or "",
                        "quantity": quantity,
                        "unit_cost": getattr(line, "unit_amount", None),
                    },
                )
                continue
    return po


def sync_clients(xero_contacts):
    """Sync Xero contacts to Client model"""
    clients = []

    for contact in xero_contacts:
        raw_json = process_xero_data(contact)

        # Check if we already have a client with this xero_contact_id
        existing_client = Client.objects.filter(
            xero_contact_id=contact.contact_id
        ).first()

        if existing_client:
            # Already linked - just update with latest Xero data
            client = existing_client
            client.raw_json = raw_json
            client.xero_last_modified = timezone.now()
            client.xero_archived = contact.contact_status == "ARCHIVED"
            client.xero_merged_into_id = getattr(contact, "merged_to_contact_id", None)
            client.save()
            created = False
        else:
            # Not linked yet - check if name already exists in our database
            contact_name = raw_json.get("_name", "").strip()
            if contact_name:
                matching_client = Client.objects.filter(name=contact_name).first()

                if matching_client:
                    if matching_client.xero_contact_id is None:
                        # Safe to link - no existing Xero ID
                        matching_client.xero_contact_id = contact.contact_id
                        matching_client.raw_json = raw_json
                        matching_client.xero_last_modified = timezone.now()
                        matching_client.xero_archived = (
                            contact.contact_status == "ARCHIVED"
                        )
                        matching_client.xero_merged_into_id = getattr(
                            contact, "merged_to_contact_id", None
                        )
                        matching_client.save()
                        logger.info(
                            f"Linked existing client '{contact_name}' (ID: {matching_client.id}) to Xero contact {contact.contact_id}"
                        )
                        client = matching_client
                        created = False
                    else:
                        # ERROR: Name exists but already linked to different Xero contact
                        raise ValueError(
                            f"Name '{contact_name}' already linked to Xero ID {matching_client.xero_contact_id}, cannot link to {contact.contact_id}"
                        )
                else:
                    # No existing client with this name - safe to create new one
                    client = Client.objects.create(
                        xero_contact_id=contact.contact_id,
                        raw_json=raw_json,
                        xero_last_modified=timezone.now(),
                        xero_archived=contact.contact_status == "ARCHIVED",
                        xero_merged_into_id=getattr(
                            contact, "merged_to_contact_id", None
                        ),
                    )
                    created = True
            else:
                # No name in contact - create anyway
                client = Client.objects.create(
                    xero_contact_id=contact.contact_id,
                    raw_json=raw_json,
                    xero_last_modified=timezone.now(),
                    xero_archived=contact.contact_status == "ARCHIVED",
                    xero_merged_into_id=getattr(contact, "merged_to_contact_id", None),
                )
                created = True

        set_client_fields(client, new_from_xero=created)
        clients.append(client)

    # Resolve merges
    for client in clients:
        if client.xero_merged_into_id and not client.merged_into:
            merged_into = Client.objects.filter(
                xero_contact_id=client.xero_merged_into_id
            ).first()
            if merged_into:
                client.merged_into = merged_into
                client.save()

    return clients


def sync_accounts(xero_accounts):
    """Sync Xero accounts"""
    for account in xero_accounts:
        XeroAccount.objects.update_or_create(
            xero_id=account.account_id,
            defaults={
                "account_code": account.code,
                "account_name": account.name,
                "description": getattr(account, "description", None),
                "account_type": account.type,
                "tax_type": account.tax_type,
                "enable_payments": getattr(
                    account, "enable_payments_to_account", False
                ),
                "xero_last_modified": account._updated_date_utc,
                "xero_last_synced": timezone.now(),
                "raw_json": process_xero_data(account),
            },
        )


def get_last_modified_time(model):
    """Get the latest modification time for a model"""
    last_modified = model.objects.aggregate(models.Max("xero_last_modified"))[
        "xero_last_modified__max"
    ]

    if last_modified:
        last_modified = last_modified - timedelta(seconds=1)
        return last_modified.isoformat()

    return "2000-01-01T00:00:00Z"


def process_xero_item(item, sync_function, entity_type):
    """Process one Xero item and return an event.

    Args:
        item: Xero object to sync.
        sync_function: Callable that saves the item.
        entity_type: Name of the entity for event messages.

    Returns:
        Tuple of success flag and event dictionary.
    """
    try:
        sync_function([item])
    except XeroValidationError as exc:
        persist_xero_error(exc)
        return False, {
            "datetime": timezone.now().isoformat(),
            "severity": "error",
            "message": str(exc),
            "progress": None,
        }
    except Exception as exc:
        persist_app_error(
            exc,
            additional_context={
                "xero_entity_type": entity_type,
                "xero_item_id": getattr(item, "id", None)
                or getattr(item, "xero_id", None),
                "operation": "sync_to_local_database",
                "sync_function": (
                    sync_function.__name__
                    if hasattr(sync_function, "__name__")
                    else str(sync_function)
                ),
            },
        )
        return False, {
            "datetime": timezone.now().isoformat(),
            "severity": "error",
            "message": "Unexpected: " + str(exc),
            "progress": None,
        }
    return True, {
        "datetime": timezone.now().isoformat(),
        "entity": entity_type,
        "severity": "info",
        "message": f"Synced {entity_type}",
        "progress": None,
    }


def sync_xero_data(
    xero_entity_type,
    our_entity_type,
    xero_api_fetch_function,
    sync_function,
    last_modified_time,
    additional_params=None,
    pagination_mode="single",
    xero_tenant_id=None,
):
    """Sync data from Xero with pagination support.

    Args:
        xero_entity_type: Name of the Xero collection.
        our_entity_type: Local entity name for messages.
        xero_api_fetch_function: API call used to fetch data.
        sync_function: Function that persists items.
        last_modified_time: Timestamp for incremental fetches.
        additional_params: Extra parameters for the API call.
        pagination_mode: Offset or page pagination style.
        xero_tenant_id: Optional tenant identifier.

    Yields:
        Progress or error events as dictionaries.
    """

    if xero_tenant_id is None:
        xero_tenant_id = get_tenant_id()

    # Production safety check
    current_machine_id = get_machine_id()
    is_production = current_machine_id == settings.PRODUCTION_MACHINE_ID

    if is_production and xero_tenant_id != settings.PRODUCTION_XERO_TENANT_ID:
        logger.warning(
            f"Attempted to sync in production with non-production tenant ID: {xero_tenant_id}"
        )
        yield {
            "datetime": timezone.now().isoformat(),
            "entity": our_entity_type,
            "severity": "warning",
            "message": "Sync aborted: Production/tenant mismatch",
            "progress": 0.0,
        }
        return

    # Setup parameters
    params = {
        "if_modified_since": last_modified_time,
        "xero_tenant_id": xero_tenant_id,
    }

    # API quirk: get_xero_items doesn't support tenant_id
    if xero_api_fetch_function == get_xero_items:
        params.pop("xero_tenant_id", None)

    # Pagination setup
    page_size = 100
    if pagination_mode == "page" and xero_entity_type not in ["quotes", "accounts"]:
        params.update({"page_size": page_size, "order": "UpdatedDateUTC ASC"})

    if additional_params:
        params.update(additional_params)

    # Fetch and process data
    page = 1
    offset = 0
    total_processed = 0

    while True:
        # Update pagination params
        if pagination_mode == "offset":
            params["offset"] = offset
        elif pagination_mode == "page":
            params["page"] = page

        # Fetch data
        entities = xero_api_fetch_function(**params)
        time.sleep(SLEEP_TIME)

        if entities is None:
            raise ValueError(f"API returned None for {xero_entity_type}")

        # Extract items
        items = (
            entities
            if isinstance(entities, list)
            else getattr(entities, xero_entity_type)
        )

        if not items:
            break

        try:
            sync_function(items)
            total_processed += len(items)
            yield {
                "datetime": timezone.now().isoformat(),
                "entity": our_entity_type,
                "severity": "info",
                "message": f"Synced {len(items)} {our_entity_type}",
                "progress": None,
            }
        except XeroValidationError as exc:
            persist_xero_error(exc)
            yield {
                "datetime": timezone.now().isoformat(),
                "severity": "error",
                "message": str(exc),
                "progress": None,
            }
        except Exception as exc:
            persist_app_error(
                exc,
                additional_context={
                    "xero_entity_type": xero_entity_type,
                    "our_entity_type": our_entity_type,
                    "operation": "bulk_sync_from_xero_api",
                    "items_count": len(items),
                    "page": page,
                    "total_processed": total_processed,
                    "sync_function": (
                        sync_function.__name__
                        if hasattr(sync_function, "__name__")
                        else str(sync_function)
                    ),
                },
            )
            yield {
                "datetime": timezone.now().isoformat(),
                "severity": "error",
                "message": "Unexpected: " + str(exc),
                "progress": None,
            }

        yield {
            "datetime": timezone.now().isoformat(),
            "entity": our_entity_type,
            "severity": "info",
            "message": f"Processed {len(items)} {our_entity_type}",
            "progress": None,
            "recordsUpdated": len(items),
        }

        # Check if done
        if len(items) < page_size or pagination_mode == "single":
            break

        # Update pagination
        if pagination_mode == "page":
            page += 1
        elif pagination_mode == "offset":
            offset = max(item.journal_number for item in items) + 1

    yield {
        "datetime": timezone.now().isoformat(),
        "entity": our_entity_type,
        "severity": "info",
        "message": f"Completed sync of {our_entity_type}",
        "status": "Completed",
        "progress": 1.0,
    }


# Entity configurations
ENTITY_CONFIGS = {
    "accounts": (
        "accounts",
        "accounts",
        XeroAccount,
        "get_accounts",
        sync_accounts,
        None,
        "single",
    ),
    "contacts": (
        "contacts",
        "contacts",
        Client,
        "get_contacts",
        sync_clients,
        {"include_archived": True},
        "page",
    ),
    "invoices": (
        "invoices",
        "invoices",
        Invoice,
        "get_invoices",
        lambda items: sync_entities(items, Invoice, "invoice_id", transform_invoice),
        {"where": 'Type=="ACCREC"'},
        "page",
    ),
    "bills": (
        "invoices",
        "bills",
        Bill,
        "get_invoices",
        lambda items: sync_entities(items, Bill, "invoice_id", transform_bill),
        {"where": 'Type=="ACCPAY"'},
        "page",
    ),
    "quotes": (
        "quotes",
        "quotes",
        Quote,
        "get_quotes",
        lambda items: sync_entities(items, Quote, "quote_id", transform_quote),
        None,
        "single",
    ),
    "credit_notes": (
        "credit_notes",
        "credit_notes",
        CreditNote,
        "get_credit_notes",
        lambda items: sync_entities(
            items, CreditNote, "credit_note_id", transform_credit_note
        ),
        None,
        "page",
    ),
    "purchase_orders": (
        "purchase_orders",
        "purchase_orders",
        PurchaseOrder,
        "get_purchase_orders",
        lambda items: sync_entities(
            items, PurchaseOrder, "purchase_order_id", transform_purchase_order
        ),
        None,
        "page",
    ),
    "stock": (
        "items",
        "stock",
        Stock,
        "get_xero_items",
        lambda items: sync_entities(items, Stock, "item_id", transform_stock),
        None,
        "single",
    ),
    "journals": (
        "journals",
        "journals",
        XeroJournal,
        "get_journals",
        lambda items: sync_entities(
            items, XeroJournal, "journal_id", transform_journal
        ),
        None,
        "offset",
    ),
}


def sync_all_xero_data(use_latest_timestamps=True, days_back=30, entities=None):
    """Sync Xero data - either using latest timestamps or looking back N days."""
    token = get_token()
    if not token:
        logger.warning("No valid Xero token found")
        return

    if entities is None:
        entities = list(ENTITY_CONFIGS.keys())

    # Get timestamps
    if use_latest_timestamps:
        timestamps = {
            entity: get_last_modified_time(ENTITY_CONFIGS[entity][2])
            for entity in ENTITY_CONFIGS
        }
    else:
        older_time = (timezone.now() - timedelta(days=days_back)).isoformat()
        timestamps = {entity: older_time for entity in ENTITY_CONFIGS}

    # Sync each entity
    for entity in entities:
        if entity not in ENTITY_CONFIGS:
            logger.error(f"Unknown entity type: {entity}")
            persist_app_error(
                ValueError(f"Unknown entity type: {entity}"),
                additional_context={
                    "operation": "sync_all_xero_data",
                    "unknown_entity": entity,
                    "available_entities": list(ENTITY_CONFIGS.keys()),
                    "requested_entities": entities,
                },
            )
            continue

        (
            xero_type,
            our_type,
            model,
            api_method,
            sync_func,
            params,
            pagination,
        ) = ENTITY_CONFIGS[entity]

        # Get API function
        if api_method == "get_xero_items":
            api_func = get_xero_items
        else:
            api_func = getattr(AccountingApi(api_client), api_method)

        yield from sync_xero_data(
            xero_entity_type=xero_type,
            our_entity_type=our_type,
            xero_api_fetch_function=api_func,
            sync_function=sync_func,
            last_modified_time=timestamps[entity],
            additional_params=params,
            pagination_mode=pagination,
        )

    # After syncing from Xero, sync local stock items back to Xero (bidirectional)
    if "stock" in entities or entities == list(ENTITY_CONFIGS.keys()):
        yield from sync_local_stock_to_xero()


def sync_local_stock_to_xero():
    """Sync local stock items to Xero as part of the main sync process."""
    try:
        yield {
            "datetime": timezone.now().isoformat(),
            "entity": "stock_local_to_xero",
            "severity": "info",
            "message": "Starting sync of local stock items to Xero",
            "progress": None,
        }

        from apps.workflow.api.xero.stock_sync import sync_all_local_stock_to_xero

        # Sync local stock items to Xero (limit to avoid overwhelming)
        result = sync_all_local_stock_to_xero(limit=50)

        if result["synced_count"] > 0:
            yield {
                "datetime": timezone.now().isoformat(),
                "entity": "stock_local_to_xero",
                "severity": "info",
                "message": f"Synced {result['synced_count']} local stock items to Xero",
                "progress": None,
                "recordsUpdated": result["synced_count"],
            }

        if result["failed_count"] > 0:
            yield {
                "datetime": timezone.now().isoformat(),
                "entity": "stock_local_to_xero",
                "severity": "warning",
                "message": f"Failed to sync {result['failed_count']} stock items to Xero",
                "progress": None,
            }

        yield {
            "datetime": timezone.now().isoformat(),
            "entity": "stock_local_to_xero",
            "severity": "info",
            "message": f"Completed local stock sync: {result['success_rate']:.1f}% success rate",
            "status": "Completed",
            "progress": 1.0,
        }

    except Exception as e:
        logger.error(f"Error syncing local stock to Xero: {str(e)}")
        persist_app_error(
            e,
            additional_context={
                "operation": "sync_local_stock_to_xero",
                "sync_direction": "local_to_xero",
            },
        )
        yield {
            "datetime": timezone.now().isoformat(),
            "entity": "stock_local_to_xero",
            "severity": "error",
            "message": f"Error syncing local stock to Xero: {str(e)}",
            "progress": None,
        }


def one_way_sync_all_xero_data(entities=None):
    """Normal sync using latest timestamps"""
    yield from sync_all_xero_data(use_latest_timestamps=True, entities=entities)


def deep_sync_xero_data(days_back=30, entities=None):
    """Perform a deep synchronisation over a time window.

    Args:
        days_back: Number of days of history to retrieve.
        entities: Optional list of entity keys to sync.

    Yields:
        Progress or error events as dictionaries.
    """
    yield from sync_all_xero_data(
        use_latest_timestamps=False, days_back=days_back, entities=entities
    )


def synchronise_xero_data(delay_between_requests=1):
    """Yield progress events while performing a full Xero synchronisation."""
    if not cache.add("xero_sync_lock", True, timeout=60 * 60 * 4):
        logger.info("Skipping sync - another sync is running")
        yield {
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "warning",
            "message": "Skipping sync - another sync is already running",
        }
        return

    try:
        company_defaults = CompanyDefaults.objects.get()
        now = timezone.now()

        # Check if deep sync needed
        if (
            not company_defaults.last_xero_deep_sync
            or (now - company_defaults.last_xero_deep_sync).days >= 30
        ):
            is_first_sync = company_defaults.last_xero_deep_sync is None
            days_to_sync = 5000 if is_first_sync else 90

            yield from deep_sync_xero_data(days_back=days_to_sync)
            company_defaults.last_xero_deep_sync = now
            company_defaults.save()

        # Normal sync
        yield from one_way_sync_all_xero_data()

        company_defaults.last_xero_sync = now
        company_defaults.save()

    finally:
        cache.delete("xero_sync_lock")


def sync_client_to_xero(client):
    """Push a client to Xero"""
    if not client.validate_for_xero():
        logger.error(f"Client {client.id} failed validation")
        return False

    accounting_api = AccountingApi(api_client)
    contact_data = client.get_client_for_xero()

    if not contact_data:
        logger.error(f"Client {client.id} failed to generate Xero data")
        return False

    if client.xero_contact_id:
        contact_data["ContactID"] = client.xero_contact_id
        response = accounting_api.update_contact(
            get_tenant_id(),
            contact_id=client.xero_contact_id,
            contacts={"contacts": [contact_data]},
        )
        time.sleep(SLEEP_TIME)
        logger.info(f"Updated client {client.name} in Xero")
    else:
        response = accounting_api.create_contacts(
            get_tenant_id(), contacts={"contacts": [contact_data]}
        )
        time.sleep(SLEEP_TIME)
        client.xero_contact_id = response.contacts[0].contact_id
        client.save()
        logger.info(
            f"Created client {client.name} in Xero with ID {client.xero_contact_id}"
        )

    return True


def sync_job_to_xero(job):
    """Push a job to Xero Projects API"""
    if not settings.XERO_SYNC_PROJECTS:
        logger.info(
            f"Skipping Xero Project sync for Job {job.job_number} "
            "(feature flag disabled)"
        )
        return False

    logger.info(f"Syncing Job {job.job_number} ({job.name}) to Xero")

    # Validation
    if not job.client:
        logger.error(f"Job {job.job_number} has no client - cannot sync to Xero")
        persist_app_error(
            ValueError(f"Job {job.job_number} has no client"),
            additional_context={
                "operation": "sync_job_to_xero",
                "job_id": str(job.id),
                "job_number": job.job_number,
                "job_name": job.name,
            },
        )
        return False

    if not job.client.xero_contact_id:
        logger.error(
            f"Job {job.job_number} client '{job.client.name}' has no xero_contact_id - sync client first"
        )
        return False

    # Validate contact exists in Xero - fail early
    try:
        valid_client = get_or_fetch_client(
            job.client.xero_contact_id, f"job {job.job_number}"
        )
        logger.info(f"Validated client exists in Xero: {valid_client.name}")
    except Exception as e:
        logger.error(
            f"Job {job.job_number} client contact_id {job.client.xero_contact_id} does not exist in Xero: {e}"
        )
        persist_app_error(
            e,
            additional_context={
                "operation": "sync_job_to_xero",
                "job_id": str(job.id),
                "job_number": job.job_number,
                "client_name": job.client.name,
                "contact_id": job.client.xero_contact_id,
            },
        )
        return False

    # Prepare project data
    project_data = {
        "name": job.name,
        "contact_id": job.client.xero_contact_id,
    }

    # Add optional fields (correct field names per SDK) - defensive programming
    if not job.delivery_date:
        # Skip deadline - it's optional in Xero
        pass
    else:
        # Convert date to timezone-aware datetime at end of day
        delivery_datetime = timezone.make_aware(
            datetime.combine(job.delivery_date, datetime.max.time())
        )
        project_data["deadline_utc"] = delivery_datetime

    # TODO: description not supported in ProjectCreateOrUpdate - set via separate API call
    # if job.description:
    #     project_data["description"] = job.description

    # TODO: status not supported in ProjectCreateOrUpdate - set via separate API call
    # # Map job status to Xero project status
    # # Most statuses → INPROGRESS, only "archived" → CLOSED
    # if job.status == "archived":
    #     project_data["status"] = "CLOSED"
    # else:
    #     project_data["status"] = "INPROGRESS"

    # Handle estimate from latest_estimate - defensive programming
    if not job.latest_estimate:
        raise ValueError(f"Job {job.job_number} has no latest_estimate")

    estimate_total = job.latest_estimate.total_revenue
    # Only set estimate_amount if greater than 0 (Xero requirement)
    if estimate_total and float(estimate_total) > 0:
        project_data["estimate_amount"] = float(estimate_total)

    try:
        if job.xero_project_id:
            # Update existing project
            logger.info(f"Updating existing Xero project {job.xero_project_id}")
            response = update_project(job.xero_project_id, project_data)
            time.sleep(SLEEP_TIME)
            logger.info(f"Updated Job {job.job_number} project in Xero")
        else:
            # Create new project
            logger.info(f"Creating new Xero project for Job {job.job_number}")
            response = create_project(project_data)
            time.sleep(SLEEP_TIME)

            # Save the project ID back to our job
            job.xero_project_id = response.project_id
            job.xero_last_synced = timezone.now()
            job.save(update_fields=["xero_project_id", "xero_last_synced"])

            logger.info(
                f"Created Job {job.job_number} in Xero with project ID {job.xero_project_id}"
            )

            # Create default Labor task for time entries
            logger.info(f"Creating default Labor task for Job {job.job_number}")
            default_task = create_default_task(job.xero_project_id)
            time.sleep(SLEEP_TIME)

            job.xero_default_task_id = default_task.task_id
            job.save(update_fields=["xero_default_task_id"])

            logger.info(
                f"Created default Labor task for Job {job.job_number} with task ID {job.xero_default_task_id}"
            )

        # Sync CostLine time/expense entries in bulk
        if job.xero_project_id:
            sync_costlines_to_xero(job)

        return True

    except Exception as e:
        logger.error(f"Failed to sync Job {job.job_number} to Xero: {e}", exc_info=True)
        persist_app_error(
            e,
            additional_context={
                "operation": "sync_job_to_xero",
                "job_id": str(job.id),
                "job_number": job.job_number,
                "job_name": job.name,
            },
        )
        return False


def sync_costlines_to_xero(job) -> bool:
    """
    Sync job CostLines to Xero Projects as time entries and expense tasks.

    Time CostLines (kind='time') -> Xero time entries with default task
    Other CostLines (material/adjust) -> Xero tasks with FIXED charge type

    Only syncs CostLines from 'actual' cost sets that have been modified
    since last sync or never synced before.
    """
    logger.info(f"Syncing CostLines for Job {job.job_number} to Xero")

    if not job.xero_project_id:
        error = ValueError(f"Job {job.job_number} has no xero_project_id")
        persist_app_error(
            error,
            additional_context={
                "operation": "sync_costlines_to_xero",
                "job_id": str(job.id),
                "job_number": job.job_number,
            },
        )
        raise error

    # Get CostLines from actual cost sets only
    actual_cost_sets = job.cost_sets.filter(kind="actual")
    if not actual_cost_sets.exists():
        logger.info(f"Job {job.job_number} has no actual cost sets - nothing to sync")
        return True

    costlines = CostLine.objects.filter(cost_set__in=actual_cost_sets).filter(
        models.Q(xero_last_synced__isnull=True)
        | models.Q(xero_last_modified__gt=models.F("xero_last_synced"))
    )

    if not costlines.exists():
        logger.info(f"Job {job.job_number} has no CostLines needing sync")
        return True

    logger.info(f"Found {costlines.count()} CostLines to sync for Job {job.job_number}")

    # Separate time entries from expenses
    time_entries = []
    expense_entries = []

    for costline in costlines:
        if costline.kind == "time":
            time_entry = map_costline_to_time_entry(costline, job.xero_default_task_id)
            time_entries.append((costline, time_entry))
        else:
            expense_entry = map_costline_to_expense_entry(costline)
            expense_entries.append((costline, expense_entry))

    # Sync time entries
    if time_entries:
        sync_time_entries_bulk(job.xero_project_id, time_entries)

    # Sync expense entries
    if expense_entries:
        sync_expense_entries_bulk(job.xero_project_id, expense_entries)

    logger.info(f"Completed CostLine sync for Job {job.job_number}")
    return True


def map_costline_to_time_entry(costline, task_id: str) -> TimeEntryCreateOrUpdate:
    """
    Map a CostLine (kind='time') to Xero TimeEntryCreateOrUpdate object.

    Converts hours (quantity) to minutes, validates staff reference in meta,
    and creates proper Xero Python library object for API calls.
    """
    staff_id = costline.meta.get("staff_id")
    if not staff_id:
        error = ValueError(f"CostLine {costline.id} has no staff_id in meta")
        persist_app_error(
            error,
            additional_context={
                "operation": "map_costline_to_time_entry",
                "costline_id": str(costline.id),
                "meta": costline.meta,
            },
        )
        raise error

    try:
        Staff.objects.get(id=staff_id)
    except Staff.DoesNotExist:
        error = ValueError(
            f"CostLine {costline.id} references non-existent staff {staff_id}"
        )
        persist_app_error(
            error,
            additional_context={
                "operation": "map_costline_to_time_entry",
                "costline_id": str(costline.id),
                "staff_id": staff_id,
            },
        )
        raise error

    # Convert hours to minutes (Xero uses minutes)
    if costline.quantity is None:
        error = ValueError(f"CostLine {costline.id} has null quantity")
        persist_app_error(
            error,
            additional_context={
                "operation": "map_costline_to_time_entry",
                "costline_id": str(costline.id),
            },
        )
        raise error

    minutes = int(float(costline.quantity) * 60)

    # Get date from costline meta - must exist
    date_str = costline.meta.get("date")
    if not date_str:
        error = ValueError(f"CostLine {costline.id} has no date in meta")
        persist_app_error(
            error,
            additional_context={
                "operation": "map_costline_to_time_entry",
                "costline_id": str(costline.id),
                "meta": costline.meta,
            },
        )
        raise error

    date_utc = datetime.fromisoformat(date_str)

    time_entry = TimeEntryCreateOrUpdate(
        description=costline.desc,
        duration=minutes,
        date_utc=date_utc,
        user_id=settings.XERO_DEFAULT_USER_ID,  # This is supposed to be the staff ID.  The code here is wrong.
        task_id=task_id,
    )

    # Skip user_id - let Xero assign to current token user

    # Include existing Xero time ID if updating
    if costline.xero_time_id:
        time_entry.time_entry_id = costline.xero_time_id

    return time_entry


def map_costline_to_expense_entry(costline) -> Dict[str, Any]:
    """
    Map a CostLine (material/adjust) to Xero task dictionary format.

    Creates FIXED charge type tasks with calculated total amount.
    These become expense tasks in Xero Projects.
    """
    if costline.quantity is None:
        error = ValueError(f"CostLine {costline.id} has null quantity")
        persist_app_error(
            error,
            additional_context={
                "operation": "map_costline_to_expense_entry",
                "costline_id": str(costline.id),
            },
        )
        raise error

    if costline.unit_cost is None:
        error = ValueError(f"CostLine {costline.id} has null unit_cost")
        persist_app_error(
            error,
            additional_context={
                "operation": "map_costline_to_expense_entry",
                "costline_id": str(costline.id),
            },
        )
        raise error

    # Calculate total amount
    total_amount = float(costline.quantity) * float(costline.unit_cost)

    expense_entry = {
        "name": costline.desc,
        "chargeType": "FIXED",
        "rate": {
            "currency": "NZD",  # NZD is correct for this NZ business
            "value": total_amount,
        },
    }

    # Include existing Xero task ID if updating
    if costline.xero_expense_id:
        expense_entry["task_id"] = costline.xero_expense_id

    return expense_entry


def sync_time_entries_bulk(project_id, time_entries_list):
    """Sync multiple time entries to Xero in bulk"""
    from .xero import create_time_entries, update_time_entries

    create_entries = []
    update_entries = []
    create_costlines = []
    update_costlines = []

    for costline, time_entry in time_entries_list:
        if costline.xero_time_id:
            update_entries.append(time_entry)
            update_costlines.append(costline)
        else:
            create_entries.append(time_entry)
            create_costlines.append(costline)

    # Create new entries
    if create_entries:
        logger.info(f"Creating {len(create_entries)} time entries")
        created = create_time_entries(project_id, create_entries)

        # Validate API response
        if len(created) != len(create_costlines):
            error = ValueError(
                f"Xero returned {len(created)} time entries but expected {len(create_costlines)}"
            )
            persist_app_error(
                error,
                additional_context={
                    "operation": "sync_time_entries_bulk",
                    "project_id": project_id,
                    "expected_count": len(create_costlines),
                    "returned_count": len(created),
                },
            )
            raise error

        # Update CostLines with returned Xero IDs
        for i, xero_entry in enumerate(created):
            costline = create_costlines[i]
            costline.xero_time_id = xero_entry.time_entry_id
            costline.xero_last_synced = timezone.now()
            costline.save(update_fields=["xero_time_id", "xero_last_synced"])

    # Update existing entries
    if update_entries:
        logger.info(f"Updating {len(update_entries)} time entries")
        update_time_entries(project_id, update_entries)
        # Update sync timestamps
        for costline in update_costlines:
            costline.xero_last_synced = timezone.now()
            costline.save(update_fields=["xero_last_synced"])


def sync_expense_entries_bulk(project_id, expense_entries_list):
    """Sync multiple expense entries to Xero in bulk"""
    from .xero import create_expense_entries, update_expense_entries

    create_entries = []
    update_entries = []
    create_costlines = []
    update_costlines = []

    for costline, expense_entry in expense_entries_list:
        if costline.xero_expense_id:
            update_entries.append(expense_entry)
            update_costlines.append(costline)
        else:
            create_entries.append(expense_entry)
            create_costlines.append(costline)

    # Create new entries
    if create_entries:
        logger.info(f"Creating {len(create_entries)} expense entries")
        created = create_expense_entries(project_id, create_entries)

        # Validate API response
        if len(created) != len(create_costlines):
            error = ValueError(
                f"Xero returned {len(created)} expense entries but expected {len(create_costlines)}"
            )
            persist_app_error(
                error,
                additional_context={
                    "operation": "sync_expense_entries_bulk",
                    "project_id": project_id,
                    "expected_count": len(create_costlines),
                    "returned_count": len(created),
                },
            )
            raise error

        # Update CostLines with returned Xero task IDs
        for i, xero_entry in enumerate(created):
            costline = create_costlines[i]
            costline.xero_expense_id = xero_entry.task_id
            costline.xero_last_synced = timezone.now()
            costline.save(update_fields=["xero_expense_id", "xero_last_synced"])

    # Update existing entries
    if update_entries:
        logger.info(f"Updating {len(update_entries)} expense entries")
        update_expense_entries(project_id, update_entries)
        # Update sync timestamps
        for costline in update_costlines:
            costline.xero_last_synced = timezone.now()
            costline.save(update_fields=["xero_last_synced"])


def get_all_xero_contacts():
    """Fetch all contacts from Xero (including archived)"""
    accounting_api = AccountingApi(api_client)
    all_contacts = []

    try:
        # Get all contacts (including archived)
        response = accounting_api.get_contacts(get_tenant_id(), include_archived=True)
        time.sleep(SLEEP_TIME)

        for contact in response.contacts:
            all_contacts.append(
                {"name": contact.name, "contact_id": contact.contact_id}
            )
            # TODO: REMOVE DEBUG - Log specific contacts we're looking for
            if contact.name in ["Johnson PLC", "Martinez LLC"]:
                logger.info(
                    f"DEBUG: Found existing contact '{contact.name}' with ID {contact.contact_id}"
                )

        # TODO: REMOVE DEBUG - Summary of what we fetched
        logger.info(f"DEBUG: Fetched {len(all_contacts)} total contacts from Xero")

    except Exception as e:
        logger.error(f"Error fetching existing contacts from Xero: {e}")
        persist_app_error(e, additional_context={"operation": "get_all_xero_contacts"})
        raise

    return all_contacts


def create_client_contact_in_xero(client):
    """Create a single client as Xero contact"""
    if not client.validate_for_xero():
        logger.warning(f"Client {client.id} failed Xero validation")
        return False

    accounting_api = AccountingApi(api_client)
    contact_data = client.get_client_for_xero()

    if not contact_data:
        logger.warning(f"Client {client.id} failed to generate Xero data")
        return False

    try:
        response = accounting_api.create_contacts(
            get_tenant_id(), contacts={"contacts": [contact_data]}
        )
        time.sleep(SLEEP_TIME)

        client.xero_contact_id = response.contacts[0].contact_id
        client.save(update_fields=["xero_contact_id"])
        return True

    except Exception as e:
        logger.error(f"Error creating client {client.name} in Xero: {e}")
        persist_app_error(
            e,
            additional_context={
                "operation": "create_client_contact_in_xero",
                "client_id": str(client.id),
                "client_name": client.name,
            },
        )
        return False


def bulk_create_contacts_in_xero(clients_to_create, batch_size=50):
    """Create multiple client contacts in Xero in batches of 50"""
    if not clients_to_create:
        return 0

    accounting_api = AccountingApi(api_client)

    total_created = 0

    for i in range(0, len(clients_to_create), batch_size):
        batch = clients_to_create[i : i + batch_size]

        # Prepare batch contact data
        contact_batch = []
        batch_client_map = {}  # Map contact name to client object

        for client in batch:
            if not client.validate_for_xero():
                logger.error(f"Client {client.name} failed Xero validation")
                persist_app_error(
                    ValueError(f"Client {client.name} failed Xero validation"),
                    additional_context={
                        "operation": "bulk_create_contacts_in_xero",
                        "client_id": str(client.id),
                        "client_name": client.name,
                    },
                )
                raise ValueError(
                    f"Client {client.name} failed Xero validation"
                )  # FAIL EARLY

            contact_data = client.get_client_for_xero()
            if not contact_data:
                logger.error(f"Client {client.name} failed to generate Xero data")
                persist_app_error(
                    ValueError(f"Client {client.name} failed to generate Xero data"),
                    additional_context={
                        "operation": "bulk_create_contacts_in_xero",
                        "client_id": str(client.id),
                        "client_name": client.name,
                    },
                )
                raise ValueError(
                    f"Client {client.name} failed to generate Xero data"
                )  # FAIL EARLY

            # FAIL EARLY: Validate required fields
            if "name" not in contact_data:
                logger.error(
                    f"Client {client.name} contact data missing 'name' field: {contact_data}"
                )
                persist_app_error(
                    ValueError(
                        f"Client {client.name} contact data missing 'name' field"
                    ),
                    additional_context={
                        "operation": "bulk_create_contacts_in_xero",
                        "client_id": str(client.id),
                        "client_name": client.name,
                        "contact_data_keys": (
                            list(contact_data.keys()) if contact_data else None
                        ),
                    },
                )
                raise ValueError(
                    f"Client {client.name} contact data missing 'name' field"
                )  # FAIL EARLY

            # Convert lowercase 'name' to uppercase 'Name' for Xero API
            if "Name" not in contact_data and "name" in contact_data:
                contact_data["Name"] = contact_data["name"]
                del contact_data["name"]

            contact_batch.append(contact_data)
            batch_client_map[contact_data["Name"]] = client

        if not contact_batch:
            logger.warning(f"No valid contacts in batch {i // batch_size + 1}")
            continue

        try:
            # Single API call for up to 50 contacts
            logger.info(
                f"Creating batch of {len(contact_batch)} contacts in Xero (batch {i // batch_size + 1})"
            )
            response = accounting_api.create_contacts(
                get_tenant_id(), contacts={"contacts": contact_batch}
            )

            # FAIL EARLY: Check for API errors before sleeping
            if not response or not response.contacts:
                raise ValueError(
                    f"Xero API returned empty response for batch {i // batch_size + 1}"
                )

            time.sleep(
                SLEEP_TIME
            )  # Single sleep for the entire batch - only after success

            # Process responses and update client records
            for created_contact in response.contacts:
                contact_name = created_contact.name
                if contact_name in batch_client_map:
                    client = batch_client_map[contact_name]
                    client.xero_contact_id = created_contact.contact_id
                    client.save(update_fields=["xero_contact_id"])
                    total_created += 1
                    logger.info(
                        f"Created Xero contact for client {client.name}: {client.xero_contact_id}"
                    )
                else:
                    logger.warning(
                        f"Could not map created contact '{contact_name}' back to client"
                    )

        except Exception as e:
            logger.error(
                f"Failed to create batch of {len(contact_batch)} contacts: {e}"
            )
            persist_app_error(
                e,
                additional_context={
                    "operation": "bulk_create_contacts_in_xero",
                    "batch_size": len(contact_batch),
                    "batch_number": i // batch_size + 1,
                    "client_names": [client.name for client in batch],
                },
            )
            raise  # FAIL EARLY

    return total_created


def seed_clients_to_xero(clients):
    """Bulk process clients: link existing contacts + create missing ones in batches of 50"""
    # Get all existing Xero contacts (one API call)
    try:
        existing_contacts = get_all_xero_contacts()
    except Exception as e:
        logger.error(f"Failed to fetch existing Xero contacts: {e}")
        persist_app_error(e, additional_context={"operation": "seed_clients_to_xero"})
        raise  # FAIL EARLY

    existing_names = {
        contact["name"].lower(): contact["contact_id"] for contact in existing_contacts
    }

    results = {"linked": 0, "created": 0, "failed": []}

    # Separate clients into link vs create lists
    clients_to_link = []
    clients_to_create = []

    # TODO: REMOVE DEBUG - Temporary debugging for duplicate contact issue
    logger.info(
        f"DEBUG: Found {len(existing_names)} existing contacts in Xero for matching"
    )

    for client in clients:
        if client.name.lower() in existing_names:
            clients_to_link.append((client, existing_names[client.name.lower()]))
            # TODO: REMOVE DEBUG
            logger.info(
                f"DEBUG: Will LINK '{client.name}' to existing contact {existing_names[client.name.lower()]}"
            )
        else:
            clients_to_create.append(client)
            # TODO: REMOVE DEBUG - Log clients that will be created (potential duplicates)
            if client.name in ["Johnson PLC", "Martinez LLC"]:
                logger.warning(
                    f"DEBUG: Will CREATE '{client.name}' - not found in existing contacts"
                )
                logger.warning(
                    f"DEBUG: Available existing contact names: {sorted(list(set([name for name in existing_names.keys() if 'johnson' in name.lower() or 'martinez' in name.lower()])))}"
                )

    # TODO: REMOVE DEBUG
    logger.info(
        f"DEBUG: Final separation - {len(clients_to_link)} to link, {len(clients_to_create)} to create"
    )

    # Process linking (fast, no API calls)
    for client, existing_contact_id in clients_to_link:
        try:
            client.xero_contact_id = existing_contact_id
            client.save(update_fields=["xero_contact_id"])
            results["linked"] += 1
            logger.info(
                f"Linked client {client.name} to existing Xero contact: {existing_contact_id}"
            )
        except Exception as e:
            logger.error(f"Error linking client {client.name}: {e}")
            persist_app_error(
                e,
                additional_context={
                    "operation": "seed_clients_to_xero_link",
                    "client_id": str(client.id),
                    "client_name": client.name,
                },
            )
            raise  # FAIL EARLY

    # Process creation in batches using dedicated function
    if clients_to_create:
        results["created"] = bulk_create_contacts_in_xero(clients_to_create)

    return results


def seed_jobs_to_xero(jobs):
    """Bulk process jobs: create Xero projects"""
    results = {"created": 0, "failed": []}

    for job in jobs:
        try:
            # Use existing sync_job_to_xero function for consistency
            success = sync_job_to_xero(job)
            if success:
                results["created"] += 1
                logger.info(
                    f"Created Xero project for job {job.name}: {job.xero_project_id}"
                )
            else:
                logger.error(f"Failed to create Xero project for job {job.name}")
                persist_app_error(
                    Exception(f"Failed to create project for {job.name}"),
                    additional_context={
                        "operation": "seed_jobs_to_xero",
                        "job_id": str(job.id),
                        "job_name": job.name,
                    },
                )
                raise Exception(
                    f"Failed to create Xero project for job {job.name}"
                )  # FAIL EARLY

        except Exception as e:
            logger.error(f"Error processing job {job.name}: {e}")
            persist_app_error(
                e,
                additional_context={
                    "operation": "seed_jobs_to_xero",
                    "job_id": str(job.id),
                    "job_name": job.name,
                },
            )
            raise  # FAIL EARLY

    return results


def sync_single_contact(sync_service, contact_id):
    """Fetch and sync a single contact from Xero by ID"""
    if not contact_id:
        raise ValueError("No contact_id provided")

    accounting_api = AccountingApi(api_client)
    response = accounting_api.get_contacts(
        sync_service.tenant_id, i_ds=[contact_id], include_archived=True
    )
    time.sleep(SLEEP_TIME)

    if not response or not response.contacts:
        raise ValueError(f"No contact found with ID {contact_id}")

    contact = response.contacts[0]
    raw_json = process_xero_data(contact)

    client, created = Client.objects.update_or_create(
        xero_contact_id=contact.contact_id,
        defaults={
            "raw_json": raw_json,
            "xero_last_modified": timezone.now(),
            "xero_archived": contact.contact_status == "ARCHIVED",
            "xero_merged_into_id": getattr(contact, "merged_to_contact_id", None),
        },
    )

    set_client_fields(client, new_from_xero=created)

    # Handle merge if needed
    if client.xero_merged_into_id and not client.merged_into:
        merged_into = Client.objects.filter(
            xero_contact_id=client.xero_merged_into_id
        ).first()
        if merged_into:
            client.merged_into = merged_into
            client.save()

    logger.info(f"Synced contact {contact_id} from webhook")


def sync_single_invoice(sync_service, invoice_id):
    """Fetch and sync a single invoice from Xero by ID"""
    if not invoice_id:
        raise ValueError("No invoice_id provided")

    accounting_api = AccountingApi(api_client)
    response = accounting_api.get_invoice(sync_service.tenant_id, invoice_id=invoice_id)
    time.sleep(SLEEP_TIME)

    if not response or not response.invoices:
        raise ValueError(f"No invoice found with ID {invoice_id}")

    xero_invoice = response.invoices[0]

    # Route to correct model based on type
    if xero_invoice.type == "ACCPAY":
        # It's a bill
        raw_json = process_xero_data(xero_invoice)
        bill, created = Bill.objects.update_or_create(
            xero_id=xero_invoice.invoice_id,
            defaults={
                "raw_json": raw_json,
                "xero_last_modified": xero_invoice._updated_date_utc,
                "xero_last_synced": timezone.now(),
            },
        )
        set_invoice_or_bill_fields(bill, "BILL", new_from_xero=created)
        logger.info(f"Synced bill {invoice_id} from webhook")

    elif xero_invoice.type == "ACCREC":
        # It's an invoice
        raw_json = process_xero_data(xero_invoice)
        invoice, created = Invoice.objects.update_or_create(
            xero_id=xero_invoice.invoice_id,
            defaults={
                "raw_json": raw_json,
                "xero_last_modified": xero_invoice._updated_date_utc,
                "xero_last_synced": timezone.now(),
            },
        )
        set_invoice_or_bill_fields(invoice, "INVOICE", new_from_xero=created)
        logger.info(f"Synced invoice {invoice_id} from webhook")
    else:
        raise ValueError(f"Unknown invoice type {xero_invoice.type} for {invoice_id}")
