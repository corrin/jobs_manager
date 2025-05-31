# workflow/views/xero_invoice_manager.py
import logging
import json
from decimal import Decimal
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone

from workflow.models.xero_account import XeroAccount

# Import base class and helpers
from .xero_base_manager import XeroDocumentManager
from .xero_helpers import format_date, parse_xero_api_error_message # Assuming format_date is needed

# Import models
from workflow.models import Invoice, Client
from job.models import Job
from workflow.enums import InvoiceStatus
from job.enums import JobPricingMethodology
from xero_python.accounting.models import LineItem, Invoice as XeroInvoice
from xero_python.exceptions import AccountingBadRequestException, ApiException # If specific exceptions handled

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
        _is_invoice_manager = True
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
        Generates invoice-specific LineItems based on job pricing method.
        """
        if not self.job:
             raise ValueError("Job is required to generate invoice line items.")

        pricing_method: JobPricingMethodology = self.job.pricing_methodology

        match pricing_method:
            case JobPricingMethodology.TIME_AND_MATERIALS:
                return self._get_time_and_materials_line_items()
            case JobPricingMethodology.FIXED_PRICE:
                return self._get_fixed_price_line_items()
            case _:
                raise ValueError(f"Unknown pricing method for job {self.job.id}: {pricing_method}")

    def _get_time_and_materials_line_items(self):
        """
        Generates LineItems for time and materials pricing.
        """
        if not self.job or not hasattr(self.job, 'latest_reality_pricing') or not self.job.latest_reality_pricing:
             raise ValueError(f"Job {self.job.id if self.job else 'Unknown'} is missing reality pricing information for T&M invoice.")

        xero_line_items = []
        xero_line_items.append(
            LineItem(
                description=f"{f"Job: {self.job.job_number}{(" - " + self.job.description)}" if self.job.description else ''}",
                quantity=1, # Typically T&M is invoiced as a single line item sum
                unit_amount=float(self.job.latest_reality_pricing.total_revenue) or 0.00,
                account_code=self._get_account_code(),
            ),
        )
        return xero_line_items

    def _get_fixed_price_line_items(self):
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
                description=f"{f"Job: {self.job.job_number}{(" - " + self.job.description)} (Fixed Price)" if self.job.description else ''}",
                quantity=1,
                unit_amount=float(self.job.latest_quote_pricing.total_revenue) or 0.00,
                account_code=self._get_account_code(),
            )
        )
        return xero_line_items

    def get_xero_document(self, type):
        """
        Creates an invoice object for Xero management or deletion.
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
                    "due_date": format_date((timezone.now() + timedelta(days=30)).replace(day=20)),
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
        try:
            # Calls the base class create_document to handle API call
            response = super().create_document()

            if response and response.invoices:
                xero_invoice_data = response.invoices[0]
                xero_invoice_id = getattr(xero_invoice_data, 'invoice_id', None)
                if not xero_invoice_id:
                     logger.error("Xero response missing invoice_id.")
                     raise ValueError("Xero response missing invoice_id.")

                invoice_url = f"https://go.xero.com/app/invoicing/edit/{xero_invoice_id}"
                invoice_number = getattr(xero_invoice_data, 'invoice_number', None)

                # Store raw response for debugging
                invoice_json = json.dumps(xero_invoice_data.to_dict(), default=str)

                # Create local Invoice record
                invoice = Invoice.objects.create(
                    xero_id=xero_invoice_id,
                    job=self.job,
                    client=self.client,
                    number=invoice_number,
                    date=timezone.now().date(), # Use current date for management
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
                # Handle non-exception API failures (e.g., empty response)
                error_msg = "No invoices found in the Xero response or failed to create invoice."
                logger.error(error_msg)
                # Attempt to extract more details if possible
                if response and hasattr(response, 'elements') and response.elements:
                     first_element = response.elements[0]
                     if hasattr(first_element, 'validation_errors') and first_element.validation_errors:
                         error_msg = "; ".join([err.message for err in first_element.validation_errors if hasattr(err, 'message')])
                     elif hasattr(first_element, 'message'):
                          error_msg = first_element.message

                return JsonResponse(
                    {"success": False, "message": error_msg},
                    status=400, 
                )
        except AccountingBadRequestException as e:
            logger.error(
                f"Xero API BadRequest during invoice creation for job {self.job.id if self.job else 'Unknown'}: {e.status} - {e.reason}", 
                exc_info=True
            )
            error_message = parse_xero_api_error_message(
                exception_body=e.body,
                default_message=f"Xero validation error ({e.status}): {e.reason}. Please contact support to check the data sent."
            )
            return JsonResponse({"success": False, "message": error_message}, status=e.status)
        except ApiException as e:
            logger.error(f"Xero API Exception during invoice creation for job {self.job.id if self.job else 'Unknown'}: {e.status} - {e.reason}", exc_info=True)
            return JsonResponse({"success": False, "message": f"Xero API Error: {e.reason}"}, status=e.status)
        except Exception as e:
            logger.exception(f"Unexpected error during invoice creation for job {self.job.id if self.job else 'Unknown'}")
            return JsonResponse({"success": False, "message": f"An unexpected error occurred ({str(e)}) while creating the invoice with Xero. Please contact support to check the data sent."}, status=500)

    def delete_document(self):
        """Deletes an invoice in Xero and locally."""
        try:
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
                     return JsonResponse({"success": True, "messages": [{"level": "success", "message": "Invoice deleted successfully."}]})
                 else:
                      error_msg = "Xero response did not confirm invoice deletion."
                      logger.error(f"{error_msg} Status: {getattr(xero_invoice_data, 'status', 'Unknown')}")
                      return JsonResponse({"success": False, "message": error_msg}, status=400) # Changed "error" to "message"
            else:
                error_msg = "No invoices found in the Xero response or failed to delete invoice."
                logger.error(error_msg)
                return JsonResponse({"success": False, "message": error_msg}, status=400) # Changed "error" to "message"
        except AccountingBadRequestException as e:
            logger.error(
                f"Xero API BadRequest during invoice deletion for job {self.job.id if self.job else 'Unknown'}: {e.status} - {e.reason}", 
                exc_info=True
            )
            error_message = parse_xero_api_error_message(
                exception_body=e.body,
                default_message=f"Xero validation error ({e.status}): {e.reason}. Please contact support to check the data sent during invoice deletion."
            )
            return JsonResponse({"success": False, "message": error_message}, status=e.status)
        except ApiException as e:
            logger.error(f"Xero API Exception during invoice deletion for job {self.job.id if self.job else 'Unknown'}: {e.status} - {e.reason}", exc_info=True)
            return JsonResponse({"success": False, "message": f"Xero API Error: {e.reason}"}, status=e.status)
        except Exception as e:
            logger.exception(f"Unexpected error during invoice deletion for job {self.job.id if self.job else 'Unknown'}")
            return JsonResponse({"success": False, "message": f"An unexpected error occurred ({str(e)}) while deleting the invoice with Xero. Please contact support to check the data sent."}, status=500)
