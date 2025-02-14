from decimal import Decimal
import logging
import time
from datetime import date, datetime, timedelta
from uuid import UUID

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models, transaction
from django.utils import timezone
from xero_python.accounting import AccountingApi

from workflow.models import CompanyDefaults
from workflow.api.xero.reprocess_xero import (
    set_client_fields,
    set_invoice_or_bill_fields,
    set_journal_fields,
)
from workflow.api.xero.xero import api_client, get_tenant_id
from workflow.models import XeroJournal, Quote
from workflow.models.client import Client
from workflow.models.invoice import Bill, CreditNote, Invoice
from workflow.models.xero_account import XeroAccount
from workflow.tasks import sync_client_task

logger = logging.getLogger("xero")


def enqueue_client_sync_tasks():
    """
    Enqueues synchronization of all clients to be processed.
    If Celery is configured, tasks will be processed asynchronously.
    If not, they will be processed synchronously.
    """
    clients_to_push = Client.objects.filter(
        django_updated_at__gt=models.F(
            "xero_last_synced"
        )  # This fixes the bug where all local clients were being pushed
    )

    for client in clients_to_push:
        if hasattr(settings, 'CELERY_BROKER_URL'):
            sync_client_task.delay(client.id)  # Send each client as an asynchronous task
            logger.info(f"Enqueued async sync task for client {client.name}.")
        else:
            sync_client_to_xero(client)  # Process synchronously
            logger.info(f"Processed sync task for client {client.name}.")


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
    xero_entity_type,
    xero_api_function,
    sync_function,
    last_modified_time,
    additional_params=None,
    pagination_mode="single",  # "single", "page", or "offset"
):
    # Note, the logic here is gnarly.  Be careful
    # There are six scenarios to handle - single/page/offset and partial/final
    # So for example single is guaranteed to always be final - to select all records
    # which means len(items) might be bigger than page_size
    # For page we need to do one page at a time.  Which means we can't fiddle
    # with the filter or the sort - otherwise the contents of each page might change
    # For offset we do an offset by Journal Number. If we added another offset
    # We'd need to pass a variable of what to offset by.
    # This is theoretically a bug since we're ordering by journal number and so
    # we might not get all changes.  But it's never going to happen because we get
    # 100 records.  It would require having more than 100 journals change at once
    # AND for the updates to be to the newer journals first
    # Anyway point is, be careful
    if pagination_mode not in ("single", "page", "offset"):
        raise ValueError("pagination_mode must be 'single', 'page', or 'offset'")

    if pagination_mode == "offset" and xero_entity_type != "journals":
        raise TypeError("We only support journals for offset currently")

    logger.info(
        "Starting sync for %s, mode=%s, since=%s",
        xero_entity_type,
        pagination_mode,
        last_modified_time,
    )

    xero_tenant_id = get_tenant_id()
    offset = 0
    page = 1
    page_size = 100

    base_params = {
        "xero_tenant_id": xero_tenant_id,
        "if_modified_since": last_modified_time,
    }

    # Only add pagination parameters for supported endpoints
    if pagination_mode == "page" and xero_entity_type != "quotes":
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

        # Fetch the entities from the API based on the prepared parameters.
        entities = xero_api_function(**params)
        items = getattr(entities, xero_entity_type, [])  # Extract the relevant data.

        if not items:
            logger.info("No items to sync.")
            return

        # Process the current batch of items
        if callable(getattr(sync_function, "delay", None)):
            # If it's a Celery task, enqueue it
            sync_function.delay(items)
        else:
            # Otherwise, run it directly
            sync_function(items)

        # Update parameters to ensure progress in pagination.
        if pagination_mode == "page":
            # Increment page for page mode.
            page += 1
        elif pagination_mode == "offset":
            # Use JournalNumber for offset progression for journals.
            max_journal_number = max(item.journal_number for item in items)
            offset = max_journal_number + 1

        # Terminate if last batch was smaller than page size.
        if len(items) < page_size or pagination_mode == "single":
            logger.info("Finished processing all items.")
            break
        else:
            # Avoid hitting API rate limits.
            time.sleep(5)


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


def sync_invoices(invoices):
    """Sync Xero invoices (ACCREC)."""
    for inv in invoices:
        xero_id = getattr(inv, "invoice_id")

        # Retrieve the client for the invoice first
        client = Client.objects.filter(xero_contact_id=inv.contact.contact_id).first()
        if not client:
            logger.warning(f"Client not found for invoice {inv.invoice_number}")
            raise ValueError(f"Client not found for invoice {inv.invoice_number}")

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
        # Retrieve the client for the bill first
        client = Client.objects.filter(
            xero_contact_id=bill_data.contact.contact_id
        ).first()
        if not client:
            logger.warning(f"Client not found for bill {bill_number}")
            continue

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
        client = Client.objects.filter(
            xero_contact_id=note_data.contact.contact_id
        ).first()
        if not client:
            logger.warning(f"Client not found for credit note {note_number}")
            continue

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


def sync_clients(xero_contacts):
    """
    Sync clients fetched from Xero API.
    """
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

            # Use Celery if configured (broker URL exists)
            if hasattr(settings, 'CELERY_BROKER_URL'):
                sync_client_task.delay(client.id)
            else:
                sync_client_to_xero(client)

        except Exception as e:
            logger.error(f"Error processing client: {str(e)}")
            logger.error(f"Client data: {raw_json}")
            raise


def sync_accounts(xero_accounts):
    for account_data in xero_accounts:
        xero_account_id = getattr(account_data, "account_id", None)
        account_code = getattr(account_data, "code", None)
        account_name = getattr(account_data, "name", None)
        account_type = getattr(account_data, "type", None)
        tax_type = getattr(account_data, "tax_type", None)
        description = getattr(account_data, "description", None)
        enable_payments = getattr(account_data, "eenable_payments_to_account", False)
        xero_last_modified = getattr(account_data, "_updated_date_utc", None)

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
        client = Client.objects.filter(
            xero_contact_id=quote_data.contact.contact_id
        ).first()

        if not client:
            logger.warning(f"Client not found for quote {xero_id}")
            continue

        quote, created = Quote.objects.update_or_create(
            xero_id=xero_id,
            defaults={
                "client": client,
                "date": quote_data.date,
                "status": quote_data.status,
                "total_excl_tax": Decimal(quote_data.sub_total),
                "total_incl_tax": Decimal(quote_data.total),
                "xero_last_modified": quote_data.updated_date_utc,
                "xero_last_synced": timezone.now(),
                "online_url": f"https://go.xero.com/app/quotes/edit/{xero_id}",
                "raw_json": serialise_xero_object(quote_data),
            },
        )

        logger.info(
            f"{'New' if created else 'Updated'} quote: {quote.xero_id} for client {client.name}"
        )


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
    
    sync_xero_data(
        xero_entity_type="contacts",
        xero_api_function=accounting_api.get_contacts,
        sync_function=sync_clients,
        last_modified_time=our_latest_contact,
        pagination_mode="page",
    )


def one_way_sync_all_xero_data():
    accounting_api = AccountingApi(api_client)

    our_latest_contact = get_last_modified_time(Client)
    our_latest_invoice = get_last_modified_time(Invoice)
    our_latest_bill = get_last_modified_time(Bill)
    our_latest_credit_note = get_last_modified_time(CreditNote)
    our_latest_account = get_last_modified_time(XeroAccount)
    our_latest_journal = get_last_modified_time(XeroJournal)

    # Just put here for lazy debugging since I can trigger this with a button
    # invoice = Invoice.objects.filter(number="INV-54021").first()
    # set_invoice_or_bill_fields(invoice, "INVOICE")
    # reprocess_all()

    sync_xero_data(
        xero_entity_type="accounts",
        xero_api_function=accounting_api.get_accounts,
        sync_function=sync_accounts,
        last_modified_time=our_latest_account,
        pagination_mode="single",
    )

    sync_xero_data(
        xero_entity_type="contacts",
        xero_api_function=accounting_api.get_contacts,
        sync_function=sync_clients,
        last_modified_time=our_latest_contact,
        pagination_mode="page",
    )

    sync_xero_data(
        xero_entity_type="invoices",
        xero_api_function=accounting_api.get_invoices,
        sync_function=sync_invoices,
        last_modified_time=our_latest_invoice,
        additional_params={"where": 'Type=="ACCREC"'},
        pagination_mode="page",
    )

    sync_xero_data(
        xero_entity_type="invoices",
        xero_api_function=accounting_api.get_invoices,
        sync_function=sync_bills,
        last_modified_time=our_latest_bill,
        additional_params={"where": 'Type=="ACCPAY"'},
        pagination_mode="page",
    )

    sync_xero_data(
        xero_entity_type="quotes",
        xero_api_function=accounting_api.get_quotes,
        sync_function=sync_quotes,
        last_modified_time=get_last_modified_time(Quote),
        pagination_mode="page",
    )

    sync_xero_data(
        xero_entity_type="credit_notes",
        xero_api_function=accounting_api.get_credit_notes,
        sync_function=sync_credit_notes,
        last_modified_time=our_latest_credit_note,
        pagination_mode="page",
    )

    sync_xero_data(
        xero_entity_type="journals",
        xero_api_function=accounting_api.get_journals,
        sync_function=sync_journals,
        last_modified_time=our_latest_journal,
        pagination_mode="offset",
    )

def synchronise_xero_data(delay_between_requests=1):
    """Bidirectional sync with Xero - pushes changes TO Xero, then pulls FROM Xero"""
    logger.info("Starting bi-directional Xero sync")

    try:
        # PUSH changes TO Xero
        # Queue client synchronization
        enqueue_client_sync_tasks()

        # PULL changes FROM Xero using existing sync
        one_way_sync_all_xero_data()

        # Log sync time
        company_defaults, _ = CompanyDefaults.objects.get_or_create(company_name="default")
        company_defaults.last_xero_sync = timezone.now()
        company_defaults.save()

        logger.info("Completed bi-directional Xero sync")
    except Exception as e:
        logger.error(f"Error during Xero sync: {str(e)}")
        raise
    logger.info("Completed bi-directional Xero sync")
