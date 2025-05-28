# workflow/xero/reprocess_xero.py
import logging
import uuid
from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_datetime

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
    """
    Set client fields from raw_json.
    If new_from_xero is True, it means the client was just created from Xero data.
    """
    raw_json = client.raw_json
    if not raw_json:
        logger.warning(f"Client {client.id} has no raw_json to process.")
        # Ensure essential fields are not None if raw_json is missing
        client.name = client.name or "Unnamed Client"
        client.xero_last_modified = client.xero_last_modified or timezone.now()
        client.save()
        return

    client.name = raw_json.get("_name", client.name or "Unnamed Client")
    # This is the general email for the contact/company
    client.email = raw_json.get("_email_address", client.email) 

    # Update xero_contact_id from raw_json if available
    # This ensures the link to the Xero contact is maintained or established.
    xero_contact_id_from_json = raw_json.get("_contact_id")
    if xero_contact_id_from_json:
        client.xero_contact_id = xero_contact_id_from_json
    
    # Attempt to get phone number from the 'DEFAULT' phone entry if available
    default_phone = ""
    if isinstance(raw_json.get("_phones"), list):
        for phone_entry in raw_json.get("_phones", []):
            if isinstance(phone_entry, dict) and phone_entry.get("_phone_type") == "DEFAULT":
                default_phone = phone_entry.get("_phone_number", "")
                break # Found default, no need to check further
    client.phone = default_phone or client.phone # Use default_phone if found, else keep existing or empty

    # Attempt to get address from the 'STREET' address entry if available
    street_address = ""
    if isinstance(raw_json.get("_addresses"), list):
        for address_entry in raw_json.get("_addresses", []):
            if isinstance(address_entry, dict) and address_entry.get("_address_type") == "STREET":
                # Concatenate address lines, city, region, postal code, country if they exist
                parts = [
                    address_entry.get("_address_line1"),
                    address_entry.get("_address_line2"),
                    address_entry.get("_address_line3"),
                    address_entry.get("_address_line4"),
                    address_entry.get("_city"),
                    address_entry.get("_region"),
                    address_entry.get("_postal_code"),
                    address_entry.get("_country"),
                ]
                street_address = ", ".join(filter(None, parts))
                break # Found street address
    client.address = street_address or client.address # Use street_address if found, else keep existing or empty
    
    client.is_account_customer = raw_json.get("_is_customer", client.is_account_customer)

    # Handle xero_last_modified
    updated_date_utc_str = raw_json.get("_updated_date_utc")
    if updated_date_utc_str:
        try:
            client.xero_last_modified = parse_datetime(updated_date_utc_str)
        except ValueError:
            logger.error(
                f"Could not parse _updated_date_utc: {updated_date_utc_str} for client {client.id}"
            )
            client.xero_last_modified = client.xero_last_modified or timezone.now()
    else:
        client.xero_last_modified = client.xero_last_modified or timezone.now()

    # Reset contact fields before populating
    client.primary_contact_name = None
    client.primary_contact_email = None
    client.additional_contact_persons = [] # Initialize as an empty list
    client.all_phones = [] # Initialize as an empty list

    # --- Populate Primary Contact ---
    root_first_name = raw_json.get("_first_name")
    root_last_name = raw_json.get("_last_name")
    root_email = raw_json.get("_email_address") # This is the main contact's email

    contact_persons_list = None
    if '_contact_persons' in raw_json and isinstance(raw_json['_contact_persons'], list):
        contact_persons_list = raw_json['_contact_persons']
    elif 'ContactPersons' in raw_json and isinstance(raw_json['ContactPersons'], list): # Fallback
        contact_persons_list = raw_json['ContactPersons']

    primary_contact_source_is_root = False
    processed_contact_person_indices = [] # To keep track of which persons from list are used

    if root_first_name or root_last_name:
        client.primary_contact_name = f"{root_first_name or ''} {root_last_name or ''}".strip()
        client.primary_contact_email = root_email # Use the main email for the primary contact from root
        primary_contact_source_is_root = True
        logger.info(f"Set primary contact for client {client.id} from root fields: Name='{client.primary_contact_name}', Email='{client.primary_contact_email}'")
    # elif contact_persons_list and len(contact_persons_list) > 0:
    #     # Use first person from _contact_persons list as primary if root names are empty
    #     person_data = contact_persons_list[0]
    #     if isinstance(person_data, dict):
    #         first_name = person_data.get('_first_name', person_data.get('FirstName', ''))
    #         last_name = person_data.get('_last_name', person_data.get('LastName', ''))
    #         email = person_data.get('_email_address', person_data.get('EmailAddress', ''))
            
    #         full_name = f"{first_name} {last_name}".strip()
    #         if full_name:
    #             client.primary_contact_name = full_name
    #         if email: # Use the email from the contact person entry
    #             client.primary_contact_email = email
    #         processed_contact_person_indices.append(0)
    #         logger.info(f"Set primary contact for client {client.id} from _contact_persons[0]: Name='{client.primary_contact_name}', Email='{client.primary_contact_email}'")
    #     else:
    #         logger.warning(f"Data for _contact_persons[0] for client {client.id} is not a dictionary: {person_data}")
    # else:
    #     logger.info(f"No primary contact information found in root fields or _contact_persons for client {client.id}.")


    # --- Populate Additional Contact Persons ---
    # This list will store all persons from the _contact_persons array in raw_json
    
    temp_additional_contacts = []
    if contact_persons_list: # Ensure contact_persons_list was populated earlier
        for idx, person_data_item in enumerate(contact_persons_list):
            if isinstance(person_data_item, dict):
                p_first_name = person_data_item.get('_first_name', person_data_item.get('FirstName', ''))
                p_last_name = person_data_item.get('_last_name', person_data_item.get('LastName', ''))
                p_email = person_data_item.get('_email_address', person_data_item.get('EmailAddress', ''))
                
                p_full_name = f"{p_first_name} {p_last_name}".strip()
                
                contact_entry = {}
                if p_full_name:
                    contact_entry["name"] = p_full_name
                if p_email:
                    contact_entry["email"] = p_email
                
                if contact_entry: # Only add if there's a name or email
                    temp_additional_contacts.append(contact_entry)
            else:
                logger.warning(f"Item at index {idx} in _contact_persons for client {client.id} is not a dictionary: {person_data_item}")
        
        client.additional_contact_persons = temp_additional_contacts
        logger.info(f"Populated additional_contact_persons for client {client.id} with {len(temp_additional_contacts)} contacts.")
    else:
        logger.info(f"No _contact_persons list found in raw_json for client {client.id} to populate additional_contact_persons.")
        
    # --- (Re-evaluation of Primary Contact if not set from root and additional_contact_persons is available) ---
    # If primary contact wasn't set from root fields, and we now have additional_contact_persons,
    # we can set the primary contact from the first entry of additional_contact_persons.
    # This simplifies the earlier primary contact logic.

    if not primary_contact_source_is_root and client.additional_contact_persons and len(client.additional_contact_persons) > 0:
        first_additional_contact = client.additional_contact_persons[0]
        client.primary_contact_name = first_additional_contact.get("name")
        client.primary_contact_email = first_additional_contact.get("email")
        logger.info(f"Set primary contact for client {client.id} from the first of additional_contact_persons: Name='{client.primary_contact_name}', Email='{client.primary_contact_email}'")
    elif not client.primary_contact_name and not client.primary_contact_email: # If still no primary contact
         logger.info(f"No primary contact information could be derived for client {client.id}.")


    # --- Populate All Phones ---
    raw_phones_list = raw_json.get("_phones")
    if isinstance(raw_phones_list, list):
        temp_all_phones = []
        for phone_entry in raw_phones_list:
            if isinstance(phone_entry, dict):
                phone_type = phone_entry.get("_phone_type", "UNKNOWN")
                
                # Extract all parts of the phone number
                # Ensure that strip() is called on a string, even if the value is None
                country_code = (phone_entry.get("_phone_country_code") or "").strip()
                area_code = (phone_entry.get("_phone_area_code") or "").strip()
                number_part = (phone_entry.get("_phone_number") or "").strip()

                # Construct the full phone number
                # Only add parts if they exist to avoid extra spaces or hyphens
                full_number_parts = []
                if country_code:
                    full_number_parts.append(f"+{country_code}")
                if area_code:
                    full_number_parts.append(area_code)
                if number_part:
                    full_number_parts.append(number_part)
                
                full_number = " ".join(full_number_parts)

                if full_number: # Only add if there's a resulting number
                    temp_all_phones.append({"type": phone_type, "number": full_number})
        client.all_phones = temp_all_phones
        logger.info(f"Populated all_phones for client {client.id} with {len(temp_all_phones)} phone numbers.")
    else:
        logger.info(f"No _phones list found or not a list in raw_json for client {client.id}.")
        
    client.xero_last_synced = timezone.now()
    client.save()

    if new_from_xero:
        logger.info(f"Client {client.name} (ID: {client.id}) created from Xero data.")
    else:
        logger.info(f"Client {client.name} (ID: {client.id}) updated from Xero data.")


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
