# workflow/xero/reprocess_xero.py
import logging
import uuid
from decimal import Decimal

from django.utils import timezone

from workflow.models import BillLineItem, XeroJournal, XeroJournalLineItem
from workflow.models.client import Client
from workflow.models.invoice import (
    Bill,
    CreditNote,
    CreditNoteLineItem,
    Invoice,
    InvoiceLineItem,
)
from workflow.models.xero_account import XeroAccount

logger = logging.getLogger("xero")


def set_invoice_or_bill_fields(document, document_type):
    """
    Process either an invoice or bill from Xero.

    Args:
        document: Instance of XeroInvoiceOrBill
        document_type: String either "INVOICE" or "BILL"
    """

    if not document.raw_json:
        raise ValueError(
            f"{document_type.title()} raw_json is empty. "
            "We better not try to process it"
        )

    is_invoice = document.raw_json.get("_type") == "ACCREC"
    is_bill = document.raw_json.get("_type") == "ACCPAY"
    is_credit_note = document.raw_json.get("_type") in ["ACCRECCREDIT", "ACCPAYCREDIT"]

    if is_invoice:
        json_document_type = "INVOICE"
    elif is_bill:
        json_document_type = "BILL"
    elif is_credit_note:
        json_document_type = "CREDIT_NOTE"

    # Validate the document matches the type
    if document_type != json_document_type:
        raise ValueError(
            f"Document type mismatch. Got {document_type} "
            f"but document appears to be a {json_document_type}"
        )

    raw_data = document.raw_json

    # Common fields that are identical between invoices and bills
    if is_credit_note:
        document.xero_id = raw_data.get("_credit_note_id")
        document.number = raw_data.get("_credit_note_number")
    else:
        document.xero_id = raw_data.get("_invoice_id")
        document.number = raw_data.get("_invoice_number")
    document.date = raw_data.get("_date")
    document.due_date = raw_data.get("_due_date")
    document.status = raw_data.get("_status")
    document.tax = raw_data.get("_total_tax")
    document.total_excl_tax = raw_data.get("_sub_total")
    document.total_incl_tax = raw_data.get("_total")
    if document_type == "CREDIT_NOTE":
        document.amount_due = raw_data.get("_remaining_credit")
    else:
        document.amount_due = raw_data.get("_amount_due")
    document.xero_last_modified = raw_data.get("_updated_date_utc")
    document.xero_last_synced = timezone.now()

    # Set or create the client/supplier
    contact_data = raw_data.get("_contact", {})
    contact_id = contact_data.get("_contact_id")
    client = Client.objects.filter(xero_contact_id=contact_id).first()
    if not client:
        raise ValueError(
            f"Client not found for {document_type.lower()} {document.number}"
        )
    document.client = client

    document.save()

    # Handle line items
    line_items_data = raw_data.get("_line_items", [])
    amount_type = raw_data.get("_line_amount_types", {}).get("_value_")

    # Determine which line item model to use
    LineItemModel = (
        InvoiceLineItem
        if is_invoice
        else BillLineItem if is_bill else CreditNoteLineItem if is_credit_note else None
    )
    document_field = (
        "invoice"
        if is_invoice
        else "bill" if is_bill else "credit_note" if is_credit_note else None
    )

    for line_item_data in line_items_data:
        line_item_id = line_item_data.get("_line_item_id")
        xero_line_id = uuid.UUID(line_item_id)
        description = line_item_data.get("_description") or "No description provided"
        quantity = line_item_data.get("_quantity", 1)
        unit_price = line_item_data.get("_unit_amount", 1)

        try:
            line_amount = float(line_item_data.get("_line_amount", 0))
            tax_amount = float(line_item_data.get("_tax_amount", 0))
        except (TypeError, ValueError):
            line_amount = 0
            tax_amount = 0

        # Fix for the GST calculation bug
        if amount_type == "Inclusive":
            line_amount_excl_tax = line_amount - tax_amount
            line_amount_incl_tax = line_amount
        else:
            line_amount_excl_tax = line_amount
            line_amount_incl_tax = line_amount + tax_amount

        # Fetch the account
        account_code = line_item_data.get("_account_code")
        account = XeroAccount.objects.filter(account_code=account_code).first()

        # Sync the line item using dynamic field name
        kwargs = {document_field: document, "xero_line_id": xero_line_id}
        line_item, created = LineItemModel.objects.update_or_create(
            **kwargs,
            defaults={
                "quantity": quantity,
                "unit_price": unit_price,
                "description": description,
                "account": account,
                "tax_amount": tax_amount,
                "line_amount_excl_tax": line_amount_excl_tax,
                "line_amount_incl_tax": line_amount_incl_tax,
            },
        )
        # print(f"{'Created' if created else 'Updated'} Line Item: "
        #       f"Amount Excl. Tax: {line_item.line_amount_excl_tax}, "
        #       f"Tax Amount: {line_item.tax_amount}, "
        #       f"Total Incl. Tax: {line_item.line_amount_incl_tax}")

def set_client_fields(client, new_from_xero=False):
    # Extract relevant fields from raw_json
    if not client.raw_json:
        raise ValueError("Client raw_json is empty.  We better not try to process it")

    raw_data = client.raw_json

    if "_contacts" in raw_data and raw_data["_contacts"]:
        raw_data = raw_data["_contacts"][0]

    # Extract basic client fields from raw JSON
    client.name = raw_data.get("_name")
    client.email = raw_data.get("_email_address")
    # Handling the phone number
    phones = raw_data.get("_phones", [])
    client.phone = phones[0].get("phone_number", "") if phones else ""

    # Handling the address
    addresses = raw_data.get("addresses", [])
    client.address = addresses[0].get("address_line1", "") if addresses else ""

    # Handling payment terms (keeping the condition from old logic)
    payment_terms = raw_data.get("payment_terms")
    client.is_account_customer = (
        payment_terms is not None and payment_terms.get("sales") is not None
    )

    # Set contact status from Xero
    client.contact_status = raw_data.get("_contact_status")

    updated_date_utc = raw_data.get("_updated_date_utc")
    if updated_date_utc:
        client.xero_last_modified = updated_date_utc
    else:
        raise ValueError("Xero last modified date is missing from the raw JSON.")
    client.xero_last_synced = timezone.now()

    if new_from_xero:
        client.django_created_at = client.xero_last_modified
        client.django_updated_at = client.xero_last_modified

    xero_contact_id = raw_data.get("_contact_id")
    client.xero_contact_id = xero_contact_id

    # Save the updated client information
    client.save()


def set_journal_fields(journal: XeroJournal):
    """
    Read the raw_json from a XeroJournal record and set all fields and line items.
    Similar to set_invoice_or_bill_fields, but for journals.
    """
    raw_data = journal.raw_json
    if not raw_data:
        raise ValueError("Journal raw_json is empty. Cannot process fields.")

    # Adjust keys to match the underscore-prefixed structure you provided
    xero_id = raw_data.get("_journal_id")
    created_date_utc = raw_data.get("_created_date_utc")
    journal_number = raw_data.get("_journal_number")
    journal_date = raw_data.get("_journal_date")
    reference = raw_data.get("_reference")
    source_id = raw_data.get("_source_id")
    source_type = raw_data.get("_source_type")

    # Use created_date_utc as xero_last_modified if no separate field
    # Keeping consistent with other models
    xero_last_modified = created_date_utc

    # Verify xero_id matches the journal's stored xero_id
    if xero_id and str(journal.xero_id) != str(xero_id):
        # This would be unusual. Raise an error to detect data mismatches early.
        raise ValueError(
            f"XeroJournal {journal.id} has xero_id={journal.xero_id}, "
            f"but raw_json has {xero_id}."
        )

    journal.journal_date = journal_date
    journal.created_date_utc = created_date_utc
    journal.journal_number = journal_number
    journal.reference = reference
    journal.source_id = source_id
    journal.source_type = source_type
    journal.xero_last_modified = xero_last_modified

    # Save changes to the journal before processing line items
    journal.save()

    # Handle JournalLines
    line_items_data = raw_data.get("_journal_lines", [])

    for line_item_data in line_items_data:
        line_id = line_item_data.get("_journal_line_id")

        # Convert amounts from strings to Decimal
        net_amount_str = line_item_data.get("_net_amount", "0")
        gross_amount_str = line_item_data.get("_gross_amount", "0")
        tax_amount_str = line_item_data.get("_tax_amount", "0")

        # Convert to Decimal
        net_amount = Decimal(net_amount_str)
        gross_amount = Decimal(gross_amount_str)
        tax_amount = Decimal(tax_amount_str)

        account_code = line_item_data.get("_account_code")
        description = line_item_data.get("_description")
        tax_type = line_item_data.get("_tax_type")
        tax_name = line_item_data.get("_tax_name")

        # Fetch the account if available
        account = XeroAccount.objects.filter(account_code=account_code).first()

        XeroJournalLineItem.objects.update_or_create(
            xero_line_id=line_id,
            journal=journal,
            defaults={
                "account": account,
                "description": description,
                "net_amount": net_amount,
                "gross_amount": gross_amount,
                "tax_amount": tax_amount,
                "tax_type": tax_type,
                "tax_name": tax_name,
                "raw_json": line_item_data,
            },
        )


def reprocess_invoices():
    """Reprocess all existing invoices to set fields based on raw JSON."""
    for invoice in Invoice.objects.all():
        try:
            set_invoice_or_bill_fields(invoice, "INVOICE")
            logger.info(f"Reprocessed invoice: {invoice.number}")
        except Exception as e:
            logger.error(f"Error reprocessing invoice {invoice.number}: {str(e)}")


def reprocess_bills():
    """Reprocess all existing bills to set fields based on raw JSON."""
    for bill in Bill.objects.all():
        try:
            set_invoice_or_bill_fields(bill, "BILL")
            logger.info(f"Reprocessed bill: {bill.number}")
        except Exception as e:
            logger.error(f"Error reprocessing bill {bill.number}: {str(e)}")


def reprocess_credit_notes():
    """Reprocess all existing credit notes to set fields based on raw JSON."""
    for credit_note in CreditNote.objects.all():
        try:
            set_invoice_or_bill_fields(credit_note, "CREDIT NOTE")
            logger.info(f"Reprocessed credit note: {credit_note.number}")
        except Exception as e:
            logger.error(
                f"Error reprocessing credit note {credit_note.number}: {str(e)}"
            )


def reprocess_clients():
    """Reprocess all existing clients to set fields based on raw JSON."""
    for client in Client.objects.all():
        try:
            set_client_fields(client)
            logger.info(f"Reprocessed client: {client.name}")
        except Exception as e:
            logger.error(f"Error reprocessing client {client.name}: {str(e)}")


def reprocess_journals():
    """
    Iterate over all XeroJournal records and re-run the set_journal_fields().
    Useful if we've tweaked mapping logic and want to re-derive fields from stored raw_json.
    """
    from workflow.models.xero_journal import XeroJournal

    for jrnl in XeroJournal.objects.all():
        try:
            set_journal_fields(jrnl)
            logger.info(f"Reprocessed journal: {jrnl.journal_number or jrnl.xero_id}")
        except Exception as e:
            logger.error(
                f"Error reprocessing journal "
                f"{jrnl.journal_number or jrnl.xero_id}: {str(e)}"
            )


def reprocess_all():
    """Reprocesses all data to set fields based on raw JSON."""
    # NOte, we don't have a reprocess accounts because it just feels too weird.
    # If you break accounts, you probably want to handle it manually
    reprocess_clients()
    reprocess_invoices()
    reprocess_bills()
    reprocess_credit_notes()
    reprocess_journals()
