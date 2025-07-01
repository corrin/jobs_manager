# workflow/views/xero_invoice_manager.py
import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.http import JsonResponse
from django.utils import timezone
from xero_python.accounting.models import Contact as XeroContact
from xero_python.accounting.models import Invoice as XeroInvoice
from xero_python.accounting.models import LineItem
from xero_python.exceptions import (  # If specific exceptions handled
    AccountingBadRequestException,
    ApiException,
)

from apps.accounting.enums import InvoiceStatus

# Import models
from apps.accounting.models import Invoice
from apps.client.models import Client
from apps.job.enums import JobPricingMethodology
from apps.job.models import Job
from apps.job.models.costing import CostSet

# Import base class and helpers
from .xero_base_manager import XeroDocumentManager
from .xero_helpers import (  # Assuming format_date is needed
    format_date,
    parse_xero_api_error_message,
)

logger = logging.getLogger("xero")


class XeroInvoiceManager(XeroDocumentManager):
    """
    Handles invoice management in Xero.
    """

    _is_invoice_manager = True

    def __init__(self, client: Client, job: Job):
        """
        Initializes the invoice manager. Both client and job are required for invoices.
        Calls the base class __init__ ensuring consistent signature.
        """
        if not client or not job:
            raise ValueError("Client and Job are required for XeroInvoiceManager")
        # Call the base class __init__ with the client and the job
        super().__init__(client=client, job=job)

    def get_xero_id(self):
        if not self.job:
            return None

        try:
            invoice = Invoice.objects.get(job=self.job)
            return str(invoice.xero_id) if invoice and invoice.xero_id else None
        except Invoice.DoesNotExist:
            return None

    def _get_xero_update_method(self):
        # Returns the Xero API method for creating/updating invoices
        return self.xero_api.update_or_create_invoices

    def _get_local_model(self):
        return Invoice

    def state_valid_for_xero(self):
        """
        Checks if the job is in a valid state to be invoiced in Xero.
        Returns True if valid, False otherwise.
        """
        # self.job is guaranteed to exist here due to the __init__ check
        return not self.job.invoiced

    def get_line_items(self):
        """
        Generate invoice LineItems using only CostSet/CostLine.
        Uses the latest CostSet of kind 'actual'.
        """
        if not self.job:
            raise ValueError("Job is required to generate invoice line items.")

        latest_actual = (
            CostSet.objects.filter(job=self.job, kind="actual")
            .order_by("-rev", "-created")
            .first()
        )
        if not latest_actual:
            raise ValueError(
                f"Job {self.job.id} does not have an 'actual' CostSet for invoicing."
            )

        # Try to get total revenue from summary, otherwise sum unit_rev from cost lines
        total_revenue = None
        if latest_actual.summary and isinstance(latest_actual.summary, dict):
            total_revenue = latest_actual.summary.get("rev")
        if total_revenue is None:
            total_revenue = sum(cl.unit_rev for cl in latest_actual.cost_lines.all())
        total_revenue = float(total_revenue or 0.0)

        description = f"Job: {self.job.job_number}"
        if self.job.description:
            description += f" - {self.job.description} (Invoice)"
        else:
            description += " (Invoice)"

        return [
            LineItem(
                description=description,
                quantity=1,
                unit_amount=total_revenue,
                account_code=self._get_account_code(),
            )
        ]

    def get_xero_document(self, type):
        """
        Creates an invoice object for Xero management or deletion.
        """
        if not self.job:
            raise ValueError("Job is required to get Xero document for an invoice.")

        match type:
            case "create":
                contact = self.get_xero_contact()
                line_items = self.get_line_items()
                base_data = {
                    "type": "ACCREC",  # Accounts Receivable
                    "contact": contact,
                    "line_items": line_items,
                    "date": format_date(timezone.now()),
                    "due_date": format_date(
                        (timezone.now() + timedelta(days=30)).replace(day=20)
                    ),
                    "line_amount_types": "Exclusive",  # Assuming Exclusive
                    "currency_code": "NZD",  # Assuming NZD
                    "status": "DRAFT",  # Create as Draft initially
                }
                # Add reference only if job has an order_number
                if hasattr(self.job, "order_number") and self.job.order_number:
                    base_data["reference"] = self.job.order_number

                return XeroInvoice(**base_data)

            case "delete":
                xero_id = self.get_xero_id()
                if not xero_id:
                    raise ValueError("Cannot delete invoice without a Xero ID.")
                # Deletion via API usually means setting status to DELETED
                # via update
                return XeroInvoice(
                    invoice_id=xero_id,
                    status="DELETED",
                    # Other fields might be required by Xero API for
                    # update/delete status change
                    # contact=self.get_xero_contact(),  # Likely not needed
                    # line_items=self.get_line_items(),  # Likely not needed
                    # date=format_date(timezone.now()), # Likely not needed
                )
            case _:
                raise ValueError(f"Unknown document type for Invoice: {type}")

    def create_document(self):
        """Creates an invoice, processes response, and stores it in the database."""
        try:
            # Calls the base class create_document to handle API call
            response = super().create_document()

            if response and response.invoices:
                xero_invoice_data = response.invoices[0]
                xero_invoice_id = getattr(xero_invoice_data, "invoice_id", None)
                if not xero_invoice_id:
                    logger.error("Xero response missing invoice_id.")
                    raise ValueError("Xero response missing invoice_id.")

                invoice_url = (
                    f"https://go.xero.com/app/invoicing/edit/{xero_invoice_id}"
                )
                invoice_number = getattr(xero_invoice_data, "invoice_number", None)

                # Store raw response for debugging
                invoice_json = json.dumps(xero_invoice_data.to_dict(), default=str)

                # Create local Invoice record
                invoice = Invoice.objects.create(
                    xero_id=xero_invoice_id,
                    job=self.job,
                    client=self.client,
                    number=invoice_number,
                    date=timezone.now().date(),  # Use current date for management
                    due_date=(
                        timezone.now().date() + timedelta(days=30)
                    ),  # Assuming 30 day terms
                    status=InvoiceStatus.SUBMITTED,  # Set local status
                    # Use getattr with defaults for safety
                    total_excl_tax=Decimal(getattr(xero_invoice_data, "sub_total", 0)),
                    tax=Decimal(getattr(xero_invoice_data, "total_tax", 0)),
                    total_incl_tax=Decimal(getattr(xero_invoice_data, "total", 0)),
                    amount_due=Decimal(getattr(xero_invoice_data, "amount_due", 0)),
                    xero_last_synced=timezone.now(),
                    # Use current time as approximation
                    xero_last_modified=timezone.now(),
                    online_url=invoice_url,
                    raw_json=invoice_json,
                )

                logger.info(
                    f"Invoice {invoice.id} created successfully for job {self.job.id}"
                )

                # Return success details for the view
                return JsonResponse(
                    {
                        "success": True,
                        "invoice_id": str(invoice.id),  # Return local ID
                        "xero_id": str(xero_invoice_id),
                        "client": self.client.name,
                        "total_excl_tax": str(invoice.total_excl_tax),
                        "total_incl_tax": str(invoice.total_incl_tax),
                        "invoice_url": invoice_url,
                    }
                )
            else:
                # Handle non-exception API failures (e.g., empty response)
                error_msg = """
                No invoices found in the Xero response or failed to create invoice.
                """.strip()
                logger.error(error_msg)
                # Attempt to extract more details if possible
                if response and hasattr(response, "elements") and response.elements:
                    first_element = response.elements[0]
                    if (
                        hasattr(first_element, "validation_errors")
                        and first_element.validation_errors
                    ):
                        error_msg = "; ".join(
                            [
                                err.message
                                for err in first_element.validation_errors
                                if hasattr(err, "message")
                            ]
                        )
                    elif hasattr(first_element, "message"):
                        error_msg = first_element.message

                return JsonResponse(
                    {"success": False, "message": error_msg},
                    status=400,
                )
        except AccountingBadRequestException as e:
            logger.error(
                (
                    f"Xero API BadRequest during invoice creation for job "
                    f"{self.job.id if self.job else 'Unknown'}: {e.status} - {e.reason}"
                ),
                exc_info=True,
            )
            default_message = (
                f"Xero validation error ({e.status}): {e.reason}. "
                "Please contact Corrin to check the data sent."
            )
            error_message = parse_xero_api_error_message(
                exception_body=e.body,
                default_message=default_message,
            )
            return JsonResponse(
                {"success": False, "message": error_message}, status=e.status
            )
        except ApiException as e:
            job_id = self.job.id if self.job else "Unknown"
            logger.error(
                f"""
                Xero API Exception during invoice creation for job {job_id}:
                {e.status} - {e.reason}
                """.strip(),
                exc_info=True,
            )
            return JsonResponse(
                {"success": False, "message": f"Xero API Error: {e.reason}"},
                status=e.status,
            )
        except Exception as e:
            job_id = self.job.id if self.job else "Unknown"
            logger.exception(
                f"Unexpected error during invoice creation for job {job_id}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "message": f"""
                    An unexpected error occurred ({str(e)}) while creating the invoice
                    with Xero. Please contact support to check the data sent.
                    """.strip(),
                },
                status=500,
            )

    def delete_document(self):
        """Deletes an invoice in Xero and locally."""
        try:
            # Calls the base class delete_document which handles the API call
            response = super().delete_document()

            if response and response.invoices:
                # Check if the response indicates successful deletion
                xero_invoice_data = response.invoices[0]
                status = str(getattr(xero_invoice_data, "status", "")).upper()
                xero_invoice_id = getattr(xero_invoice_data, "invoice_id", None)
                if status == "DELETED" and xero_invoice_id:
                    # Remove local Invoice if exists
                    deleted_count = Invoice.objects.filter(
                        xero_id=xero_invoice_id
                    ).delete()[0]
                    logger.info(
                        f"Invoice {xero_invoice_id} deleted in Xero and {deleted_count} local record(s) removed."
                    )
                    return JsonResponse(
                        {
                            "success": True,
                            "xero_id": str(xero_invoice_id),
                            "message": "Invoice deleted successfully in Xero and locally.",
                        }
                    )
                else:
                    error_msg = f"Invoice deletion failed or status not DELETED. Status: {status}, Xero ID: {xero_invoice_id}"
                    logger.error(error_msg)
                    return JsonResponse(
                        {"success": False, "message": error_msg}, status=400
                    )
            else:
                error_msg = """
                No invoices found in the Xero response or failed to delete invoice.
                """.strip()
                logger.error(error_msg)
                return JsonResponse(
                    {"success": False, "message": error_msg}, status=400
                )
        except AccountingBadRequestException as e:
            job_id = self.job.id if self.job else "Unknown"
            logger.error(
                f"""
                Xero API BadRequest during invoice deletion for job {job_id}:
                {e.status} - {e.reason}
                """.strip(),
                exc_info=True,
            )
            error_message = parse_xero_api_error_message(
                exception_body=e.body,
                default_message=f"""
                Xero validation error ({e.status}): {e.reason}.
                Please contact support to check the data sent during invoice deletion.
                """.strip(),
            )
            return JsonResponse(
                {"success": False, "message": error_message}, status=e.status
            )
        except ApiException as e:
            job_id = self.job.id if self.job else "Unknown"
            logger.error(
                f"""
                Xero API Exception during invoice deletion for job {job_id}:
                {e.status} - {e.reason}
                """.strip(),
                exc_info=True,
            )
            return JsonResponse(
                {"success": False, "message": f"Xero API Error: {e.reason}"},
                status=e.status,
            )
        except Exception as e:
            job_id = self.job.id if self.job else "Unknown"
            logger.exception(
                f"Unexpected error during invoice deletion for job {job_id}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "message": f"""
                    An unexpected error occurred ({str(e)}) while deleting the invoice
                    with Xero. Please contact support to check the data sent.
                    """.strip(),
                },
                status=500,
            )

    def get_or_create_xero_contact(self):
        """
        Searches for an existing Xero contact by client name. If found, returns the Contact object with ContactID.
        If not found, creates a new contact and returns the created Contact object.
        """
        client_name = (
            self.client.name.strip() if self.client and self.client.name else None
        )
        if not client_name:
            raise ValueError("Client name is required to sync with Xero.")

        try:
            # Search for existing contacts in Xero by name (case-insensitive)
            contacts_response = self.xero_api.get_contacts(
                self.xero_tenant_id, where=f'Name=="{client_name}"'
            )
            contacts = getattr(contacts_response, "contacts", [])
            if contacts:
                logger.info(
                    f"Found existing Xero contact for '{client_name}' (ContactID: {contacts[0].contact_id})"
                )
                return contacts[0]  # Return the first found contact
        except Exception as e:
            logger.warning(f"Error searching for existing Xero contact: {str(e)}")
            # Do not interrupt the flow, try to create contact below

        # If not found, create new contact
        logger.info(
            f"No existing Xero contact found for '{client_name}', creating new contact."
        )
        contact_data = {
            "name": client_name,
            "email_address": getattr(self.client, "email", None),
            "first_name": getattr(self.client, "first_name", None),
            "last_name": getattr(self.client, "last_name", None),
            # Add other relevant fields if necessary
        }
        # Remove None fields
        contact_data = {k: v for k, v in contact_data.items() if v}
        new_contact = XeroContact(**contact_data)
        try:
            create_response = self.xero_api.create_contacts(
                self.xero_tenant_id, contacts=[new_contact]
            )
            created_contacts = getattr(create_response, "contacts", [])
            if created_contacts:
                logger.info(
                    f"Created new Xero contact for '{client_name}' (ContactID: {created_contacts[0].contact_id})"
                )
                return created_contacts[0]
        except Exception as e:
            logger.error(f"Failed to create Xero contact for '{client_name}': {str(e)}")
            raise ValueError(
                f"Could not create or find Xero contact for '{client_name}'. {str(e)}"
            )
        raise ValueError(f"Could not create or find Xero contact for '{client_name}'.")

    def get_xero_contact(self):
        """
        Returns the Xero contact (with ContactID if already exists, or new if not).
        """
        return self.get_or_create_xero_contact()
