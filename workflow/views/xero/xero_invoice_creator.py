# workflow/views/xero_invoice_creator.py
import logging
import json
from decimal import Decimal
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone

# Import base class and helpers
from .xero_base_creator import XeroDocumentCreator
from .xero_helpers import format_date # Assuming format_date is needed

# Import models
from workflow.models import Invoice, Job, Client # Add Job, Client if needed by methods
from workflow.enums import InvoiceStatus, JobPricingType
from xero_python.accounting.models import LineItem, Invoice as XeroInvoice
from xero_python.exceptions import AccountingBadRequestException # If specific exceptions handled

logger = logging.getLogger("xero")

class XeroInvoiceCreator(XeroDocumentCreator):
    """
    Handles invoice creation in Xero.
    """
    def __init__(self, client, job):
        """
        Initializes the invoice creator. Both client and job are required for invoices.
        Calls the base class __init__ ensuring consistent signature.
        """
        if not client or not job:
             raise ValueError("Client and Job are required for XeroInvoiceCreator")
        # Call the base class __init__ with the client and the job
        super().__init__(client=client, job=job)

    def get_xero_id(self):
        # self.job is guaranteed to exist here due to the __init__ check
        return str(self.job.invoice.xero_id) if hasattr(self.job, "invoice") and self.job.invoice else None

    def get_xero_update_method(self):
        # Returns the Xero API method for creating/updating invoices
        return self.xero_api.update_or_create_invoices

    def get_local_model(self):
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
        Generates invoice-specific LineItems based on job pricing type.
        """
        if not self.job:
             raise ValueError("Job is required to generate invoice line items.")

        pricing_type: JobPricingType = self.job.pricing_type

        match pricing_type:
            case JobPricingType.TIME_AND_MATERIALS:
                return self.get_time_and_materials_line_items()
            case JobPricingType.FIXED_PRICE:
                return self.get_fixed_price_line_items()
            case _:
                raise ValueError(f"Unknown pricing type for job {self.job.id}: {pricing_type}")

    def get_time_and_materials_line_items(self):
        """
        Generates LineItems for time and materials pricing.
        """
        if not self.job or not hasattr(self.job, 'latest_reality_pricing') or not self.job.latest_reality_pricing:
             raise ValueError(f"Job {self.job.id if self.job else 'Unknown'} is missing reality pricing information for T&M invoice.")

        xero_line_items = []
        xero_line_items.append(
            LineItem(
                description=f"Job: {self.job.job_number}{(" - " + self.job.description) if self.job.description else ''}",
                quantity=1, # Typically T&M is invoiced as a single line item sum
                unit_amount=float(self.job.latest_reality_pricing.total_revenue) or 0.00,
                account_code="200", # Assuming account code 200 for revenue # FIXME: Get this from a lookup to XeroAccount, not hardcoded
            ),
        )
        return xero_line_items

    def get_fixed_price_line_items(self):
        """
        Generates LineItems for fixed price pricing based on the quote.
        """
        if not self.job or not hasattr(self.job, 'latest_quote_pricing') or not self.job.latest_quote_pricing:
             raise ValueError(f"Job {self.job.id if self.job else 'Unknown'} is missing quote pricing information for Fixed Price invoice.")

        xero_line_items: list[LineItem] = []
        # It seems the original code added an empty description line first - keeping for consistency?
        # xero_line_items.append(LineItem(description="Price as quoted")) # Consider if this is needed
        xero_line_items.append(
            LineItem(
                description=f"Job: {self.job.job_number}{(" - " + self.job.description) if self.job.description else ''} (Fixed Price)",
                quantity=1,
                unit_amount=float(self.job.latest_quote_pricing.total_revenue) or 0.00,
                account_code="200", # Assuming account code 200 for revenue # FIXME: Get this from a lookup to XeroAccount, not hardcoded
            )
        )
        return xero_line_items

    def get_xero_document(self, type):
        """
        Creates an invoice object for Xero creation or deletion.
        """
        if not self.job:
             raise ValueError("Job is required to get Xero document for an invoice.")

        match (type):
            case "create":
                contact = self.get_xero_contact()
                line_items = self.get_line_items()
                base_data = {
                    "type": "ACCREC", # Accounts Receivable
                    "contact": contact,
                    "line_items": line_items,
                    "date": format_date(timezone.now()),
                    "due_date": format_date(timezone.now() + timedelta(days=30)), # Assuming 30 day terms
                    "line_amount_types": "Exclusive", # Assuming Exclusive
                    "currency_code": "NZD", # Assuming NZD
                    "status": "DRAFT", # Create as Draft initially
                }
                # Add reference only if job has an order_number
                if hasattr(self.job, 'order_number') and self.job.order_number:
                    base_data["reference"] = self.job.order_number

                return XeroInvoice(**base_data)

            case "delete":
                xero_id = self.get_xero_id()
                if not xero_id:
                     raise ValueError("Cannot delete invoice without a Xero ID.")
                # Deletion via API usually means setting status to DELETED via update
                return XeroInvoice(
                    invoice_id=xero_id,
                    status="DELETED",
                    # Other fields might be required by Xero API for update/delete status change
                    # contact=self.get_xero_contact(), # Likely not needed
                    # line_items=self.get_line_items(), # Likely not needed
                    # date=format_date(timezone.now()), # Likely not needed
                )
            case _:
                 raise ValueError(f"Unknown document type for Invoice: {type}")

    def create_document(self):
        """Creates an invoice, processes response, and stores it in the database."""
        # Calls the base class create_document to handle API call
        response = super().create_document()

        if response and response.invoices:
            xero_invoice_data = response.invoices[0]
            xero_invoice_id = getattr(xero_invoice_data, 'invoice_id', None)
            if not xero_invoice_id:
                 logger.error("Xero response missing invoice_id.")
                 raise ValueError("Xero response missing invoice_id.")

            invoice_url = f"https://go.xero.com/app/invoices/edit/{xero_invoice_id}"
            invoice_number = getattr(xero_invoice_data, 'invoice_number', None)

            # Store raw response for debugging
            invoice_json = json.dumps(xero_invoice_data.to_dict(), default=str)

            # Create local Invoice record
            invoice = Invoice.objects.create(
                xero_id=xero_invoice_id,
                job=self.job,
                client=self.client,
                number=invoice_number,
                date=timezone.now().date(), # Use current date for creation
                due_date=(timezone.now().date() + timedelta(days=30)), # Assuming 30 day terms
                status=InvoiceStatus.SUBMITTED, # Set local status
                # Use getattr with defaults for safety
                total_excl_tax=Decimal(getattr(xero_invoice_data, 'sub_total', 0)),
                tax=Decimal(getattr(xero_invoice_data, 'total_tax', 0)),
                total_incl_tax=Decimal(getattr(xero_invoice_data, 'total', 0)),
                amount_due=Decimal(getattr(xero_invoice_data, 'amount_due', 0)),
                xero_last_synced=timezone.now(),
                xero_last_modified=timezone.now(), # Use current time as approximation
                online_url=invoice_url,
                raw_json=invoice_json,
            )

            logger.info(f"Invoice {invoice.id} created successfully for job {self.job.id}")

            # Return success details for the view
            return JsonResponse(
                {
                    "success": True,
                    "invoice_id": str(invoice.id), # Return local ID
                    "xero_id": str(xero_invoice_id),
                    "client": self.client.name,
                    "total_excl_tax": str(invoice.total_excl_tax),
                    "total_incl_tax": str(invoice.total_incl_tax),
                    "invoice_url": invoice_url,
                }
            )
        else:
            # Handle API failure or unexpected response
            error_msg = "No invoices found in the Xero response or failed to create invoice."
            logger.error(error_msg)
            # Attempt to extract more details if possible
            if response and hasattr(response, 'elements') and response.elements:
                 first_element = response.elements[0]
                 if hasattr(first_element, 'validation_errors') and first_element.validation_errors:
                     error_msg = "; ".join([err.message for err in first_element.validation_errors])
                 elif hasattr(first_element, 'message'):
                      error_msg = first_element.message

            return JsonResponse(
                {"success": False, "error": error_msg},
                status=400, # Use 400 for API/validation errors
            )

    def delete_document(self):
        """Deletes an invoice in Xero and locally."""
        # Calls the base class delete_document which handles the API call
        response = super().delete_document()

        if response and response.invoices:
             # Check if the response indicates successful deletion (e.g., status is DELETED)
             xero_invoice_data = response.invoices[0]
             if str(getattr(xero_invoice_data, 'status', '')).upper() == 'DELETED':
                 # Delete local record only after confirming Xero deletion/update
                 if hasattr(self.job, 'invoice') and self.job.invoice:
                     local_invoice_id = self.job.invoice.id
                     self.job.invoice.delete()
                     logger.info(f"Invoice {local_invoice_id} deleted successfully for job {self.job.id}")
                 else:
                      logger.warning(f"No local invoice found for job {self.job.id} to delete.")
                 return JsonResponse({"success": True})
             else:
                  error_msg = "Xero response did not confirm invoice deletion."
                  logger.error(f"{error_msg} Status: {getattr(xero_invoice_data, 'status', 'Unknown')}")
                  return JsonResponse({"success": False, "error": error_msg}, status=400)
        else:
            error_msg = "No invoices found in the Xero response or failed to delete invoice."
            logger.error(error_msg)
            return JsonResponse({"success": False, "error": error_msg}, status=400)