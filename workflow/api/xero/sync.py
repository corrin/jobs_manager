from decimal import Decimal
import logging
import time
from datetime import date, datetime, timedelta
from uuid import UUID

from django.core.cache import cache
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models, transaction
from django.utils import timezone
from xero_python.accounting import AccountingApi
from xero_python.exceptions.http_status_exceptions import RateLimitException

from workflow.models import CompanyDefaults
from workflow.api.xero.reprocess_xero import (
    set_client_fields,
    set_invoice_or_bill_fields,
    set_journal_fields,
)
from workflow.api.xero.xero import api_client, get_tenant_id, get_token
from workflow.models import XeroJournal, Quote
from workflow.models.client import Client
from workflow.models.invoice import Bill, CreditNote, Invoice
from workflow.models.xero_account import XeroAccount
from workflow.models.purchase import PurchaseOrder, PurchaseOrderLine
logger = logging.getLogger("xero")


def apply_rate_limit_delay(response_headers):
    """
    Applies a dynamic delay based on the 'Retry-After' header returned by Xero.
    This is needed in case we get a 429 error (rate limit exceeded).
    """
    retry_after = int(response_headers.get("Retry-After", 0))
    if retry_after > 0:
        logger.warning(f"Rate limit reached. Retrying after {retry_after} seconds...")
        time.sleep(retry_after)


def sync_xero_data(
    xero_entity_type,  # The entity type as known in Xero's API
    our_entity_type,   # The entity type as known in our system
    xero_api_fetch_function,
    sync_function,
    last_modified_time,
    additional_params=None,
    pagination_mode="single",  # "single", "page", or "offset"
):
    if pagination_mode not in ("single", "page", "offset"):
        raise ValueError("pagination_mode must be 'single', 'page', or 'offset'")

    if pagination_mode == "offset" and xero_entity_type != "journals":
        raise TypeError("We only support journals for offset currently")

    logger.info(
        "Starting sync for %s, mode=%s, since=%s",
        our_entity_type,
        pagination_mode,
        last_modified_time,
    )

    yield {
        "datetime": timezone.now().isoformat(),
        "entity": our_entity_type,
        "severity": "info",
        "message": f"Starting sync for {our_entity_type} since {last_modified_time}",
        "progress": 0.0,
        "lastSync": last_modified_time
    }

    xero_tenant_id = get_tenant_id()
    offset = 0
    page = 1
    page_size = 100
    total_processed = 0
    total_items = None
    current_batch_start = 0

    base_params = {
        "xero_tenant_id": xero_tenant_id,
        "if_modified_since": last_modified_time,
    }

    # Only add pagination parameters for supported endpoints
    if pagination_mode == "page" and xero_entity_type not in ["quotes", "accounts"]:
        # Page mode uses UpdatedDateUTC ordering for consistent incremental fetching.
        base_params.update({"page_size": page_size, "order": "UpdatedDateUTC ASC"})

    if additional_params:
        base_params.update(additional_params)

    while True:
        # Prepare the API parameters for this iteration.
        params = dict(base_params)
        if pagination_mode == "offset":
            params["offset"] = offset
        elif pagination_mode == "page":
            params["page"] = page

        try:
            # Fetch the entities from the API based on the prepared parameters.
            logger.debug(f"Making API call for {xero_entity_type} with params: {params}")
            entities = xero_api_fetch_function(**params)
            if entities is None:
                logger.error(f"API call returned None for {xero_entity_type}")
                raise ValueError(f"API call returned None for {xero_entity_type}")
            items = getattr(entities, xero_entity_type, [])  # Extract the relevant data.

            if not items:
                logger.info("No items to sync.")
                yield {
                    "datetime": timezone.now().isoformat(),
                    "entity": our_entity_type,
                    "severity": "info",
                    "message": "No items to sync",
                    "progress": 1.0,
                    "lastSync": timezone.now().isoformat()
                }
                return

            # Get total items for progress tracking
            match xero_entity_type:
                case entity if entity in ["contacts", "invoices", "credit_notes", "purchase_orders"]:
                    total_items = entities.pagination.item_count
                    yield {
                        "datetime": timezone.now().isoformat(),
                        "entity": our_entity_type,
                        "severity": "info",
                        "message": f"Found {total_items} {our_entity_type} to sync",
                        "progress": 0.0,
                        "totalItems": total_items
                    }
                case "accounts":
                    total_items = len(items)  # For accounts, we get all items at once
                    yield {
                        "datetime": timezone.now().isoformat(),
                        "entity": our_entity_type,
                        "severity": "info",
                        "message": f"Found {total_items} accounts to sync",
                        "progress": 0.0,
                        "totalItems": total_items
                    }
                case "journals":
                    total_items = len(items)  # For journals, we get all items at once
                    yield {
                        "datetime": timezone.now().isoformat(),
                        "entity": our_entity_type,
                        "severity": "info",
                        "message": f"Found {total_items} journals to sync",
                        "progress": 0.0,
                        "totalItems": total_items
                    }
                case "quotes":
                    total_items = len(items)  # For quotes, we get all items at once
                    yield {
                        "datetime": timezone.now().isoformat(),
                        "entity": our_entity_type,
                        "severity": "info",
                        "message": f"Found {total_items} quotes to sync",
                        "progress": 0.0,
                        "totalItems": total_items
                    }
                case _:
                    raise ValueError(f"Unexpected entity type: {xero_entity_type}")

            # Process the current batch of items
            try:
                sync_function(items)
                total_processed += len(items)
                
                # Calculate progress based on entity type
                progress = None
                if total_items:
                    progress = min(total_processed / total_items, 0.99)  # Cap at 99% until complete
                
                # Prepare progress message based on entity type
                match xero_entity_type:
                    case "journals":
                        current_batch_end = max(item.journal_number for item in items)
                        message = f"Processed journals {current_batch_start} to {current_batch_end}"
                    case entity if entity in ["contacts", "invoices", "credit_notes", "purchase_orders"]:
                        message = f"Processed {total_processed} of {total_items} {our_entity_type}"
                    case "quotes":
                        message = f"Processed {total_processed} of {total_items} quotes"
                    case "accounts":
                        message = f"Processed {total_processed} of {total_items} accounts"
                    case _:
                        raise ValueError(f"Unexpected entity type: {xero_entity_type}")
                
                yield {
                    "datetime": timezone.now().isoformat(),
                    "entity": our_entity_type,
                    "severity": "info",
                    "message": message,
                    "progress": progress,
                    "lastSync": timezone.now().isoformat(),
                    "processedCount": total_processed,
                    "totalCount": total_items
                }

            except Exception as e:
                logger.error(f"Error in sync function for {our_entity_type}: {str(e)}")
                yield {
                    "datetime": timezone.now().isoformat(),
                    "entity": our_entity_type,
                    "severity": "error",
                    "message": f"Error processing {our_entity_type}: {str(e)}",
                    "progress": None,
                    "lastSync": last_modified_time
                }
                raise

            # Update parameters to ensure progress in pagination.
            if pagination_mode == "page":
                # Increment page for page mode.
                page += 1
            elif pagination_mode == "offset":
                # Use JournalNumber for offset progression for journals.
                max_journal_number = max(item.journal_number for item in items)
                offset = max_journal_number + 1

            # Terminate if last batch was smaller than page size or if it's accounts
            if len(items) < page_size or pagination_mode == "single":
                logger.info("Finished processing all items.")
                yield {
                    "datetime": timezone.now().isoformat(),
                    "entity": our_entity_type,
                    "severity": "info",
                    "message": f"Completed sync of {total_processed} {our_entity_type}",
                    "progress": 1.0,
                    "lastSync": timezone.now().isoformat(),
                    "processedCount": total_processed,
                    "totalCount": total_items
                }
                break
            else:
                # Avoid hitting API rate limits
                time.sleep(5)

        except RateLimitException as e:
            # Use the apply_rate_limit_delay function to handle rate limiting
            logger.warning(f"Rate limit hit when syncing {our_entity_type}. Applying dynamic delay.")
            retry_after = int(e.response_headers.get("Retry-After", 0))
            yield {
                "datetime": timezone.now().isoformat(),
                "entity": our_entity_type,
                "severity": "warning",
                "message": f"Rate limit hit, waiting {retry_after} seconds",
                "progress": None,
                "lastSync": last_modified_time
            }
            apply_rate_limit_delay(e.response_headers)
            # Continue the loop to retry after the delay
            continue


def get_last_modified_time(model):
    """
    Fetch the latest 'last_modified' from the given model, or default to a far past date.
    We use this to see what needs to sync to Xero.  Anything newer than this in Xero
    needs to be synced to us
    """
    last_modified_time = model.objects.aggregate(models.Max("xero_last_modified"))[
        "xero_last_modified__max"
    ]
    if last_modified_time:
        # The handling of milliseconds differs between django and Xero.
        # This simplifies things by simply syncing them again
        last_modified_time = last_modified_time - timedelta(seconds=1)

    if last_modified_time:
        last_modified_str = last_modified_time.isoformat()
    else:
        last_modified_str = "2000-01-01T00:00:00Z"

    logger.info(f"{model.__name__}: Using last_modified_time={last_modified_str}")

    return last_modified_str


def serialise_xero_object(obj):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, (list, tuple)):
        return [serialise_xero_object(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialise_xero_object(value) for key, value in obj.items()}
    elif hasattr(obj, "__dict__"):
        return serialise_xero_object(obj.__dict__)
    else:
        return str(obj)


def remove_junk_json_fields(data):
    """We delete currency fields because they're really bulky and repeated on every invoice"""
    exclude_keys = {"_currency_code", "_currency_rate"}

    if isinstance(data, dict):
        # Recursively remove currency fields from the dictionary
        return {
            key: remove_junk_json_fields(value)
            for key, value in data.items()
            if key not in exclude_keys
        }
    elif isinstance(data, list):
        # Recursively apply this function for lists of items
        return [remove_junk_json_fields(item) for item in data]
    else:
        return data  # Base case: return data as-is if it's not a dict or list


def clean_raw_json(data):
    def is_unwanted_field(key, value):
        unwanted_patterns = [
            "_value2member_map_",
            "_generate_next_value_",
            "_member_names_",
            "__objclass__",
        ]
        return any(pattern in key for pattern in unwanted_patterns)

    def recursively_clean(data):
        if isinstance(data, dict):
            return {
                k: recursively_clean(v)
                for k, v in data.items()
                if not is_unwanted_field(k, v)
            }
        elif isinstance(data, list):
            return [recursively_clean(i) for i in data]
        else:
            return data

    return recursively_clean(data)


def get_or_fetch_client_by_contact_id(contact_id, invoice_number=None):
    """
    Get a client by Xero contact_id, fetching it from the API if not found locally.
    Args:
        contact_id: The Xero contact_id to search for.
        invoice_number: Optional invoice number for logging purposes.
    
    Returns:
        Client: The client instance found or fetched.
    
    Raises:
        ValueError: If the client is not found in Xero.
    """
    client = Client.objects.filter(xero_contact_id=contact_id).first()
    if client:
        return client
    
    missing_client = AccountingApi(api_client).get_contact(get_tenant_id(), contact_id)
    if not missing_client:
        entity_ref = f"invoice {invoice_number}" if invoice_number else f"contact ID {contact_id}"
        logger.warning(f"Client not found for {entity_ref}")
        raise ValueError(f"Client not found for {entity_ref}")

    synced_clients = sync_clients([missing_client], sync_back_to_xero=False)
    if not synced_clients:
        entity_ref = f"invoice {invoice_number}" if invoice_number else f"contact ID {contact_id}"
        logger.warning(f"Client not found for {entity_ref}")
        raise ValueError(f"Client not found for {entity_ref}")
    return synced_clients[0]


def sync_invoices(invoices):
    """Sync Xero invoices (ACCREC)."""
    for inv in invoices:
        xero_id = getattr(inv, "invoice_id")

        # Retrieve the client for the invoice first
        try:
            client = get_or_fetch_client_by_contact_id(
                inv.contact.contact_id,     
                inv.invoice_number
            )
        except ValueError as e:
            logger.error(f"Error processing invoice {inv.invoice_number}: {str(e)}")
            raise

        dirty_raw_json = serialise_xero_object(inv)
        raw_json = clean_raw_json(dirty_raw_json)

        # Retrieve or create the invoice (without saving initially)
        try:
            invoice = Invoice.objects.get(xero_id=xero_id)
            created = False
        except Invoice.DoesNotExist:
            invoice = Invoice(xero_id=xero_id, client=client)
            created = True

        # Perform the rest of the operations
        try:
            # Update raw_json
            invoice.raw_json = raw_json

            # Set other fields from raw_json using set_invoice_fields
            set_invoice_or_bill_fields(invoice, "INVOICE")

            # Log whether the invoice was created or updated
            if created:
                logger.info(
                    f"New invoice added: {invoice.number} "
                    f"updated_at={invoice.xero_last_modified}"
                )
            else:
                logger.info(
                    f"Updated invoice: {invoice.number} "
                    f"updated_at={invoice.xero_last_modified}"
                )

        except Exception as e:
            logger.error(f"Error processing invoice {inv.invoice_number}: {str(e)}")
            logger.error(f"Invoice data: {raw_json}")
            raise


def sync_bills(bills):
    """Sync Xero bills (ACCPAY)."""
    for bill_data in bills:
        xero_id = getattr(bill_data, "invoice_id")
        dirty_raw_json = serialise_xero_object(bill_data)
        raw_json = clean_raw_json(dirty_raw_json)
        bill_number = raw_json["_invoice_number"]
        
        # Retrieve the client for the bill
        try:
            client = get_or_fetch_client_by_contact_id(
                bill_data.contact.contact_id,
                bill_number
            )
        except ValueError as e:
            logger.error(f"Error processing bill {bill_number}: {str(e)}")
            raise

        # Retrieve or create the bill without saving immediately
        try:
            bill = Bill.objects.get(xero_id=xero_id)
            created = False
        except Bill.DoesNotExist:
            bill = Bill(xero_id=xero_id, client=client)
            created = True

        # Now perform the rest of the operations, ensuring everything is set before saving
        try:
            # Update raw_json and other necessary fields
            bill.raw_json = raw_json

            # Set other fields using set_bill_fields (which also saves the bill)
            set_invoice_or_bill_fields(bill, "BILL")

            # Log whether the bill was created or updated
            if created:
                logger.info(
                    f"New bill added: {bill.number} "
                    f"updated_at={bill.xero_last_modified}"
                )
            else:
                logger.info(
                    f"Updated bill: {bill.number} "
                    f"updated_at={bill.xero_last_modified}"
                )

        except Exception as e:
            logger.error(f"Error processing bill {bill_number}: {str(e)}")
            logger.error(f"Bill data: {raw_json}")
            raise


def sync_credit_notes(notes):
    """Sync Xero credit notes."""
    for note_data in notes:
        xero_id = getattr(note_data, "credit_note_id")
        dirty_raw_json = serialise_xero_object(note_data)
        raw_json = clean_raw_json(dirty_raw_json)
        note_number = raw_json["_credit_note_number"]

        # Retrieve the client for the credit note
        try:
            client = get_or_fetch_client_by_contact_id(
                note_data.contact.contact_id,
                note_number
            )
        except ValueError as e:
            logger.error(f"Error processing credit note {note_number}: {str(e)}")
            raise

        # Retrieve or create the credit note without saving immediately
        try:
            note = CreditNote.objects.get(xero_id=xero_id)
            created = False
        except CreditNote.DoesNotExist:
            note = CreditNote(xero_id=xero_id, client=client)
            created = True

        # Now perform the rest of the operations
        try:
            # Update raw_json and other necessary fields
            note.raw_json = raw_json

            # Set other fields using set_invoice_or_bill_fields
            set_invoice_or_bill_fields(note, "CREDIT_NOTE")

            # Log whether the credit note was created or updated
            if created:
                logger.info(
                    f"New credit note added: {note.number} "
                    f"updated_at={note.xero_last_modified}"
                )
            else:
                logger.info(
                    f"Updated credit note: {note.number} "
                    f"updated_at={note.xero_last_modified}"
                )

        except Exception as e:
            logger.error(f"Error processing credit note {note_number}: {str(e)}")
            logger.error(f"Note data: {raw_json}")
            raise


def sync_journals(journals):
    """Sync Xero journals."""
    for jrnl_data in journals:
        xero_id = getattr(jrnl_data, "journal_id")
        dirty_raw_json = serialise_xero_object(jrnl_data)
        raw_json = clean_raw_json(dirty_raw_json)

        # Retrieve the journal_number from raw_json
        # Adjust key if needed, based on your raw JSON structure
        journal_number = raw_json["_journal_number"]

        # Retrieve or create the journal without saving immediately
        try:
            journal = XeroJournal.objects.get(xero_id=xero_id)
            created = False
        except XeroJournal.DoesNotExist:
            journal = XeroJournal(xero_id=xero_id)
            created = True

        # Now perform the rest of the operations
        try:
            # Update raw_json
            journal.raw_json = raw_json

            # Set other fields using set_journal_fields
            set_journal_fields(journal)

            # Log whether the journal was created or updated
            if created:
                logger.info(
                    f"New journal added: {journal_number} "
                    f"updated_at={journal.xero_last_modified}"
                )
            else:
                logger.info(
                    f"Updated journal: {journal_number} "
                    f"updated_at={journal.xero_last_modified}"
                )

        except Exception as e:
            logger.error(f"Error processing journal {journal_number}: {str(e)}")
            logger.error(f"Journal data: {raw_json}")
            raise


def sync_clients(xero_contacts, sync_back_to_xero=True):
    """
    Sync clients fetched from Xero API.
    Returns a list of Client instances that were created or updated.
    """
    client_instances = []
    
    for contact_data in xero_contacts:
        xero_contact_id = getattr(contact_data, "contact_id", None)

        # Serialize and clean the JSON received from the API
        raw_json_with_currency = serialise_xero_object(contact_data)
        raw_json = remove_junk_json_fields(raw_json_with_currency)

        try:
            client = Client.objects.filter(xero_contact_id=xero_contact_id).first()

            if client:
                client.raw_json = raw_json
                set_client_fields(client, new_from_xero=False)
                logger.info(
                    f"Updated client: {client.name} "
                    f"updated_at={client.xero_last_modified}"
                )
            else:
                client = Client.objects.create(
                    xero_contact_id=xero_contact_id,
                    xero_last_modified=timezone.now(),
                    raw_json=raw_json,
                )
                set_client_fields(client, new_from_xero=True)
                logger.info(
                    f"New client added: {client.name} "
                    f"updated_at={client.xero_last_modified}"
                )

            if sync_back_to_xero:
                sync_client_to_xero(client)
            client_instances.append(client)

        except Exception as e:
            logger.error(f"Error processing client: {str(e)}")
            logger.error(f"Client data: {raw_json}")
            raise
    
    return client_instances


def sync_accounts(xero_accounts):
    """Sync Xero accounts."""
    logger.debug(f"sync_accounts received: {xero_accounts}")
    if xero_accounts is None:
        logger.error("xero_accounts is None - API call likely failed")
        raise ValueError("xero_accounts is None - API call likely failed")
    
    # Get all current Xero account IDs from the API response
    current_xero_ids = {getattr(account, "account_id") for account in xero_accounts}
    
    # Disabled: This code is handy if you delete accounts in Xero, since the sync doesn't do this automatically
    # # Delete any accounts that no longer exist in Xero
    # deleted_count = XeroAccount.objects.exclude(xero_id__in=current_xero_ids).delete()[0]
    # if deleted_count > 0:
    #     logger.warning(f"Deleted {deleted_count} accounts that no longer exist in Xero")
        
    for account_data in xero_accounts:
        xero_account_id = getattr(account_data, "account_id")
        account_code = getattr(account_data, "code")
        account_name = getattr(account_data, "name")
        account_type = getattr(account_data, "type")
        tax_type = getattr(account_data, "tax_type")
        description = getattr(account_data, "description", None)
        enable_payments = getattr(account_data, "enable_payments_to_account", False)
        xero_last_modified = getattr(account_data, "_updated_date_utc")

        raw_json = serialise_xero_object(account_data)

        try:
            account, created = XeroAccount.objects.update_or_create(
                xero_id=xero_account_id,
                defaults={
                    "account_code": account_code,
                    "account_name": account_name,
                    "description": description,
                    "account_type": account_type,
                    "tax_type": tax_type,
                    "enable_payments": enable_payments,
                    "xero_last_modified": xero_last_modified,
                    "xero_last_synced": timezone.now(),
                    "raw_json": raw_json,
                },
            )

            if created:
                logger.info(
                    f"New account added: {account.account_name} ({account.account_code})"
                )
            else:
                logger.info(
                    f"Updated account: {account.account_name} ({account.account_code})"
                )
        except Exception as e:
            logger.error(f"Error processing account {account_name}: {str(e)}")
            logger.error(f"Account data: {raw_json}")
            raise


def sync_quotes(quotes):
    """
    Sync Quotes fetched from Xero API.
    """
    for quote_data in quotes:
        xero_id = getattr(quote_data, "quote_id")
        
        # Retrieve the client for the quote
        try:
            client = get_or_fetch_client_by_contact_id(
                quote_data.contact.contact_id,
                f"quote {xero_id}"
            )
        except ValueError as e:
            logger.error(f"Error processing quote {xero_id}: {str(e)}")
            raise

        # Serialize the quote data first
        raw_json = serialise_xero_object(quote_data)
        
        try:
            # Extract status - should always be a dict with _value_ from Xero API
            status_data = raw_json.get("_status")
            if not isinstance(status_data, dict) or "_value_" not in status_data:
                logger.error(f"Invalid status data structure from Xero for quote {xero_id}: {status_data}")
                raise ValueError(f"Quote {xero_id} has invalid status structure from Xero API")
            
            status = status_data["_value_"]
            
            quote, created = Quote.objects.update_or_create(
                xero_id=xero_id,
                defaults={
                    "client": client,
                    "date": raw_json.get("_date"),
                    "status": status,
                    "total_excl_tax": Decimal(str(raw_json.get("_sub_total", "0"))),
                    "total_incl_tax": Decimal(str(raw_json.get("_total", "0"))),
                    "xero_last_modified": raw_json.get("_updated_date_utc"),
                    "xero_last_synced": timezone.now(),
                    "online_url": f"https://go.xero.com/app/quotes/edit/{xero_id}",
                    "raw_json": raw_json,
                },
            )

            logger.info(
                f"{'New' if created else 'Updated'} quote: {quote.xero_id} for client {client.name}"
            )
        except Exception as e:
            logger.error(f"Error processing quote {xero_id}: {str(e)}")
            logger.error(f"Quote data: {raw_json}")
            raise


def sync_purchase_orders(purchase_orders):
    """
    Sync Purchase Orders fetched from Xero API.
    """
    for po_data in purchase_orders:
        xero_id = getattr(po_data, "purchase_order_id")
        
        # Retrieve the supplier for the purchase order
        try:
            client = get_or_fetch_client_by_contact_id(
                po_data.contact.contact_id,
                po_data.purchase_order_number
            )
        except ValueError as e:
            logger.error(f"Error processing purchase order {po_data.purchase_order_number}: {str(e)}")
            raise
        
        # Serialize and clean the JSON received from the API
        raw_json = serialise_xero_object(po_data)
        
        try:
            # Retrieve or create the purchase order
            try:
                purchase_order = PurchaseOrder.objects.get(xero_id=xero_id)
                created = False
            except PurchaseOrder.DoesNotExist:
                purchase_order = PurchaseOrder(xero_id=xero_id, supplier=client)
                created = True

            # Update fields from Xero data
            purchase_order.po_number = po_data.purchase_order_number
            purchase_order.order_date = po_data.date
            purchase_order.expected_delivery = po_data.delivery_date
            
            # Set Xero sync fields
            purchase_order.xero_last_modified = raw_json.get("_updated_date_utc")
            purchase_order.xero_last_synced = timezone.now()
            
            # Map Xero status to our status
            xero_status = po_data.status
            if xero_status == "DRAFT":
                purchase_order.status = "draft"
            elif xero_status == "SUBMITTED":
                purchase_order.status = "submitted"
            elif xero_status == "AUTHORISED":
                purchase_order.status = "submitted"
            elif xero_status == "BILLED":
                purchase_order.status = "fully_received"
            elif xero_status == "DELETED":
                purchase_order.status = "void"
            else:
                purchase_order.status = "draft"  # Default

            purchase_order.save()

            # Process line items
            if hasattr(po_data, "line_items") and po_data.line_items:
                for line_item in po_data.line_items:
                    # Create or update line item
                    po_line, line_created = PurchaseOrderLine.objects.update_or_create(
                        purchase_order=purchase_order,
                        item_code=line_item.item_code or "",
                        description=line_item.description,
                        defaults={
                            "quantity": line_item.quantity,
                            "unit_cost": line_item.unit_amount,
                        }
                    )
                    
                    if line_created:
                        logger.info(f"Created line item for PO {purchase_order.po_number}: {line_item.description}")
                    else:
                        logger.info(f"Updated line item for PO {purchase_order.po_number}: {line_item.description}")

            if created:
                logger.info(f"New purchase order added: {purchase_order.po_number}")
            else:
                logger.info(f"Updated purchase order: {purchase_order.po_number}")

        except Exception as e:
            logger.error(f"Error processing purchase order {getattr(po_data, 'purchase_order_number', 'unknown')}: {str(e)}")
            logger.error(f"Purchase order data: {raw_json}")
            raise


def sync_client_to_xero(client):
    """
    Sync a client from the local database to Xero - either create a new one or update an existing one.
    """

    # Step 1: Validate client data before attempting to sync
    if not client.validate_for_xero():
        logger.error(
            f"Client {client.id} failed validation and will not be synced to Xero."
        )
        return False  # Exit early if validation fails

    xero_tenant_id = get_tenant_id()  # Fetch Xero tenant ID
    accounting_api = AccountingApi(api_client)  # Initialize the Accounting API for Xero

    # Step 2: Log sync attempt
    logger.info(f"Attempting to sync client {client.name} with Xero.")

    # Step 3: Prepare client data for Xero using the model method
    contact_data = client.get_client_for_xero()
    if not contact_data:
        logger.error(
            f"Client {client.id} failed validation and will not be synced to Xero."
        )
        return False  # Exit early if validation fails

    # Step 4: Create or update the client in Xero
    try:
        # Add a small delay before making the API call to avoid rate limits
        time.sleep(1)
        
        if client.xero_contact_id:
            # Update existing contact
            contact_data["ContactID"] = client.xero_contact_id
            response = accounting_api.update_contact(
                xero_tenant_id,
                contact_id=client.xero_contact_id,
                contacts={"contacts": [contact_data]},
            )
            logger.info(f"Updated existing client {client.name} in Xero.")
        else:
            # Create new contact
            response = accounting_api.create_contacts(
                xero_tenant_id, contacts={"contacts": [contact_data]}
            )
            # Save the new Xero ContactID to the local database
            new_contact_id = response.contacts[0].contact_id
            client.xero_contact_id = new_contact_id
            client.save()
            logger.info(
                f"Created new client {client.name} in Xero with ID {new_contact_id}."
            )

        return response.contacts if response.contacts else []
    except RateLimitException as e:
        # Use the apply_rate_limit_delay function to handle rate limiting
        logger.warning(f"Rate limit hit when syncing client {client.name}. Applying dynamic delay.")
        apply_rate_limit_delay(e.response_headers)
        # Re-raise the exception to be handled by the outer function
        raise
    except Exception as e:
        logger.error(f"Failed to sync client {client.name} to Xero: {str(e)}")
        raise


def single_sync_client(
    client_identifier=None, xero_contact_id=None, client_name=None, delete_local=False
):
    """
    Sync a single client from Xero to the app. Supports lookup by internal ID, Xero ID, or client name.
    Optionally deletes the local client before syncing from Xero if `delete_local` is set to True.
    """
    # Step 1: Initialize APIs
    xero_tenant_id = get_tenant_id()
    accounting_api = AccountingApi(api_client)

    # Step 2: Get the client
    try:
        # Fetch by internal ID if provided
        if client_identifier:
            client = Client.objects.get(id=client_identifier)

        # Fetch by Xero contact ID if provided
        elif xero_contact_id:
            client = Client.objects.get(xero_contact_id=xero_contact_id)

        # Fetch by client name if provided
        elif client_name:
            clients = Client.objects.filter(name=client_name)

            if clients.count() > 1:
                raise MultipleObjectsReturned(
                    f"Multiple clients found for name {client_name}. "
                    "Please refine the search."
                )
            elif clients.count() == 1:
                client = clients.first()
            else:
                raise ObjectDoesNotExist(f"No client found for name {client_name}.")

        if not client:
            raise ObjectDoesNotExist(
                "No valid client found with the given identifiers."
            )

        logger.info(f"Attempting to sync client {client.name} with Xero.")

    except ObjectDoesNotExist as e:
        logger.error(str(e))
        raise
    except MultipleObjectsReturned as e:
        logger.error(str(e))
        raise

    # Step 3: Optionally delete the client from the local database if delete_local is True
    if delete_local:
        try:
            with transaction.atomic():
                client.delete()
                logger.info(
                    f"Client {client_name or client_identifier} deleted from the database."
                )
        except Client.DoesNotExist:
            logger.info(
                f"Client {client_name or client_identifier} does not exist in the database."
            )

    # Step 4: Fetch the client from Xero
    try:
        response = accounting_api.get_contacts(
            xero_tenant_id,
            i_ds=[xero_contact_id] if xero_contact_id else None,
            where=(
                f'Name=="{client_name}"'
                if client_name and not xero_contact_id
                else None
            ),
        )

        contacts = response.contacts if response.contacts else []
        logger.info(contacts)

        if not contacts:
            logger.error(
                f"Client {client_name or client_identifier} not found in Xero."
            )
            raise

        xero_client = contacts[0]  # Assuming the first match
    except Exception as e:
        logger.error(
            f"Failed to fetch client {client_name or client_identifier} "
            f"from Xero: {str(e)}"
        )
        raise

    # Step 5: Sync the client back into the database
    try:
        sync_clients([xero_client])  # Call your existing sync function for clients
        logger.info(
            f"Successfully synced client {client_name or client_identifier} "
            "back into the database."
        )
    except Exception as e:
        logger.error(
            f"Failed to sync client {client_name or client_identifier} "
            f"into the database: {str(e)}"
        )
        raise


def single_sync_invoice(
    invoice_identifier=None, xero_invoice_id=None, invoice_number=None
):
    # Step 1: Initialize APIs
    xero_tenant_id = get_tenant_id()
    accounting_api = AccountingApi(api_client)

    # Step 2: Get the invoice
    try:
        # Fetch by internal ID if provided
        if invoice_identifier:
            invoice = Invoice.objects.get(id=invoice_identifier)

        # Fetch by Xero invoice ID if provided
        elif xero_invoice_id:
            invoice = Invoice.objects.get(xero_invoice_id=xero_invoice_id)

        # Fetch by invoice number if provided
        elif invoice_number:
            invoices = Invoice.objects.filter(number=invoice_number)

            if invoices.count() > 1:
                raise MultipleObjectsReturned(
                    f"Multiple invoices found for number {invoice_number}. "
                    "Please refine the search."
                )
            elif invoices.count() == 1:
                invoice = invoices.first()
            else:
                raise ObjectDoesNotExist(
                    f"No invoice found for number {invoice_number}."
                )

        if not invoice:
            raise ObjectDoesNotExist(
                "No valid invoice found with the given identifiers."
            )

        logger.info(f"Attempting to sync invoice {invoice.number} with Xero.")

    except ObjectDoesNotExist as e:
        logger.error(str(e))
        raise
    except MultipleObjectsReturned as e:
        logger.error(str(e))
        raise

    # Step 3: Delete the invoice from the local database
    try:
        with transaction.atomic():
            invoice.delete()
            logger.info(f"Invoice {invoice_number} deleted from the database.")
    except Invoice.DoesNotExist:
        logger.info(f"Invoice {invoice_number} does not exist in the database.")

    # Step 4: Fetch the invoice from Xero
    try:
        response = accounting_api.get_invoices(
            xero_tenant_id,
            invoice_numbers=[invoice_number],
            #            summary_only=False  # I found I didn't need this.  If we have < 100 invoices then it syncs enough detail
        )

        invoices = response.invoices if response.invoices else []
        logging.info(invoices)
        if not invoices:
            logger.error(f"Invoice {invoice_number} not found in Xero.")
            raise
    except Exception as e:
        logger.error(f"Failed to fetch invoice {invoice_number} from Xero: {str(e)}")
        raise

    # Step 5: Sync the invoice back into the database
    try:
        sync_invoices(invoices)  # Call your existing sync function
        logger.info(
            f"Successfully synced invoice {invoice_number} back into the database."
        )
    except Exception as e:
        logger.error(
            f"Failed to sync invoice {invoice_number} into the database: {str(e)}"
        )


def sync_xero_clients_only():
    """Sync only client data from Xero."""
    accounting_api = AccountingApi(api_client)
    our_latest_contact = get_last_modified_time(Client)
    
    yield from sync_xero_data(
        xero_entity_type="contacts",
        our_entity_type="contacts",
        xero_api_fetch_function=accounting_api.get_contacts,
        sync_function=sync_clients,
        last_modified_time=our_latest_contact,
        pagination_mode="page",
    )


def _sync_all_xero_data(use_latest_timestamps=True, days_back=30):
    """
    Internal function to sync all Xero data.
    Args:
        use_latest_timestamps: If True, use latest modification times. If False, use days_back.
        days_back: Number of days to look back when use_latest_timestamps is False.
    """
    token = get_token()
    if not token:
        logger.warning("No valid Xero token found")

    accounting_api = AccountingApi(api_client)
    logger.info("Created accounting_api")

    # Determine timestamps based on sync type
    if use_latest_timestamps:
        # Use latest timestamps from our database for normal sync
        logger.info("Performing normal sync using latest timestamps from database.")
        timestamps = {
            'contact': get_last_modified_time(Client),
            'invoice': get_last_modified_time(Invoice),
            'bill': get_last_modified_time(Bill),
            'credit_note': get_last_modified_time(CreditNote),
            'account': get_last_modified_time(XeroAccount),
            'journal': get_last_modified_time(XeroJournal),
            'quote': get_last_modified_time(Quote),
            'purchase_order': get_last_modified_time(PurchaseOrder),
        }
    else:
        # Use fixed timestamp from days_back (covers both regular deep syncs, and the initial sync)
        older_time = (timezone.now() - timedelta(days=days_back)).isoformat()
        logger.info(f"Performing deep sync using fixed timestamp going back {days_back} days: {older_time}")
        timestamps = {
            'contact': older_time,
            'invoice': older_time,
            'bill': older_time,
            'credit_note': older_time,
            'account': older_time,
            'journal': older_time,
            'quote': older_time,
            'purchase_order': older_time,
        }

    logger.info("Starting first sync_xero_data call for accounts")

    yield from sync_xero_data(
        xero_entity_type="accounts",
        our_entity_type="accounts",
        xero_api_fetch_function=accounting_api.get_accounts,
        sync_function=sync_accounts,
        last_modified_time=timestamps['account'],
        pagination_mode="single",
    )

    yield from sync_xero_data(
        xero_entity_type="contacts",
        our_entity_type="contacts",
        xero_api_fetch_function=accounting_api.get_contacts,
        sync_function=sync_clients,
        last_modified_time=timestamps['contact'],
        pagination_mode="page",
    )

    yield from sync_xero_data(
        xero_entity_type="invoices",
        our_entity_type="invoices",
        xero_api_fetch_function=accounting_api.get_invoices,
        sync_function=sync_invoices,
        last_modified_time=timestamps['invoice'],
        additional_params={"where": 'Type=="ACCREC"'},
        pagination_mode="page",
    )

    yield from sync_xero_data(
        xero_entity_type="invoices",  # Note: Still "invoices" in Xero
        our_entity_type="bills",      # But "bills" in our system
        xero_api_fetch_function=accounting_api.get_invoices,
        sync_function=sync_bills,
        last_modified_time=timestamps['bill'],
        additional_params={"where": 'Type=="ACCPAY"'},
        pagination_mode="page",
    )

    yield from sync_xero_data(
        xero_entity_type="quotes",
        our_entity_type="quotes",
        xero_api_fetch_function=accounting_api.get_quotes,
        sync_function=sync_quotes,
        last_modified_time=timestamps['quote'],
        pagination_mode="single",
    )

    yield from sync_xero_data(
        xero_entity_type="credit_notes",
        our_entity_type="credit_notes",
        xero_api_fetch_function=accounting_api.get_credit_notes,
        sync_function=sync_credit_notes,
        last_modified_time=timestamps['credit_note'],
        pagination_mode="page",
    )

    yield from sync_xero_data(
        xero_entity_type="purchase_orders",
        our_entity_type="purchase_orders",
        xero_api_fetch_function=accounting_api.get_purchase_orders,
        sync_function=sync_purchase_orders,
        last_modified_time=timestamps['purchase_order'],
        pagination_mode="page",
    )
    
    yield from sync_xero_data(
        xero_entity_type="journals",
        our_entity_type="journals",
        xero_api_fetch_function=accounting_api.get_journals,
        sync_function=sync_journals,
        last_modified_time=timestamps['journal'],
        pagination_mode="offset",
    )



def one_way_sync_all_xero_data():
    """Sync all Xero data using latest modification times."""
    yield from _sync_all_xero_data(use_latest_timestamps=True)

def deep_sync_xero_data(days_back=30):
    """
    Sync all Xero data using a longer time window (days_back).
    Args:
        days_back: Number of days to look back for changes.
    """
    logger.info(f"Starting deep sync looking back {days_back} days")
    yield {
        "datetime": timezone.now().isoformat(),
        "entity": "sync",
        "severity": "info",
        "message": f"Starting deep sync looking back {days_back} days",
        "progress": None
    }
    yield from _sync_all_xero_data(use_latest_timestamps=False, days_back=days_back)

def synchronise_xero_data(delay_between_requests=1):
    """Bidirectional sync with Xero - pushes changes TO Xero, then pulls FROM Xero"""
    if not cache.add('xero_sync_lock', True, timeout=(60 * 60 * 4)):  # 4 hours
        logger.info("Skipping sync - another sync is running")
        yield {
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "warning",
            "message": "Skipping sync - another sync is already running",
            "progress": None
        }
        return

    logger.info("Starting bi-directional Xero sync")
    yield {
        "datetime": timezone.now().isoformat(),
        "entity": "sync",
        "severity": "info",
        "message": "Starting Xero sync",
        "progress": 0.0
    }

    try:
        # PUSH changes TO Xero
        # Queue client synchronization
        # enqueue_client_sync_tasks()

        company_defaults = CompanyDefaults.objects.get()
        now = timezone.now()

        # Check if deep sync is needed (not run in last 30 days)
        if (not company_defaults.last_xero_deep_sync or
            (now - company_defaults.last_xero_deep_sync).days >= 30):
            logger.info("Deep sync needed - looking back 90 days")
            yield {
                "datetime": timezone.now().isoformat(),
                "entity": "sync",
                "severity": "info",
                "message": "Starting deep sync - looking back 90 days",
                "progress": None
            }
            # Determine if this is the very first sync and set lookback period accordingly
            is_first_sync = company_defaults.last_xero_deep_sync is None
            days_to_sync = 5000 if is_first_sync else 90 # ~13 years for first sync, 90 days otherwise
            log_message = f"Starting {'first' if is_first_sync else 'periodic'} deep sync - looking back {days_to_sync} days"
            logger.info(log_message)
            # Update the yielded message as well
            yield {
                "datetime": timezone.now().isoformat(),
                "entity": "sync",
                "severity": "info",
                "message": log_message, # Use the dynamic log message
                "progress": None
            }
            # Pass the calculated days_back, remove is_first_sync flag
            yield from deep_sync_xero_data(days_back=days_to_sync)
            company_defaults.last_xero_deep_sync = now
            company_defaults.save()
            logger.info("Deep sync completed")

        # PULL changes FROM Xero using existing sync
        yield {
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "info",
            "message": "Starting normal sync",
            "progress": None
        }
        yield from one_way_sync_all_xero_data()

        # Log sync time
        company_defaults.last_xero_sync = now
        company_defaults.save()

        logger.info("Completed bi-directional Xero sync")
        yield {
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "info",
            "message": "Completed Xero sync",
            "progress": 1.0
        }
    except Exception as e:
        logger.error(f"Error during Xero sync: {str(e)}")
        yield {
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "error",
            "message": f"Error during sync: {str(e)}",
            "progress": None
        }
        raise
    finally:
        cache.delete('xero_sync_lock')


def delete_client_from_xero(client):
    """
    Delete a client from Xero.
    """
    if not client.xero_contact_id:
        logger.info(f"Client {client.name} has no Xero contact ID - skipping Xero deletion")
        return True

    xero_tenant_id = get_tenant_id()
    accounting_api = AccountingApi(api_client)

    try:
        accounting_api.delete_contact(
            xero_tenant_id,
            client.xero_contact_id
        )
        logger.info(f"Successfully deleted client {client.name} from Xero")
        return True
    except Exception as e:
        logger.error(f"Failed to delete client {client.name} from Xero: {str(e)}")
        raise


def archive_clients_in_xero(clients, batch_size=50):
    """
    Archive multiple clients in Xero in batches.
    Returns a tuple of (success_count, error_count).
    """
    if not clients:
        return 0, 0

    xero_tenant_id = get_tenant_id()
    accounting_api = AccountingApi(api_client)
    success_count = 0
    error_count = 0
    
    # Process in batches to avoid rate limits
    for i in range(0, len(clients), batch_size):
        batch = clients[i:i + batch_size]
        contacts_data = {
            "contacts": [
                {
                    "ContactID": client.xero_contact_id,
                    "ContactStatus": "ARCHIVED"
                }
                for client in batch
                if client.xero_contact_id
            ]
        }
        
        if not contacts_data["contacts"]:
            continue
            
        try:
            accounting_api.update_or_create_contacts(
                xero_tenant_id,
                contacts=contacts_data
            )
            success_count += len(contacts_data["contacts"])
            
            # Add a small delay between batches to avoid rate limits
            if i + batch_size < len(clients):
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Failed to archive batch of clients in Xero: {str(e)}")
            error_count += len(contacts_data["contacts"])
            
    return success_count, error_count


def delete_clients_from_xero(clients):
    """
    Delete multiple clients from Xero.
    Returns a tuple of (success_count, error_count).
    """
    if not clients:
        return 0, 0

    xero_tenant_id = get_tenant_id()
    accounting_api = AccountingApi(api_client)
    success_count = 0
    error_count = 0
    
    for client in clients:
        if not client.xero_contact_id:
            logger.info(f"Client {client.name} has no Xero contact ID - skipping Xero deletion")
            continue
            
        try:
            accounting_api.delete_contact(
                xero_tenant_id,
                client.xero_contact_id
            )
            success_count += 1
            logger.info(f"Successfully deleted client {client.name} from Xero")
            
            # Add a small delay between deletions to avoid rate limits
            time.sleep(1)
            
        except Exception as e:
            error_count += 1
            logger.error(f"Failed to delete client {client.name} from Xero: {str(e)}")
            raise
            
    return success_count, error_count

