# workflow/views/xero_quote_creator.py
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
from workflow.models import Quote, Job, Client # Add Job, Client if needed by methods
from workflow.enums import QuoteStatus
from xero_python.accounting.models import LineItem, Quote as XeroQuote
from xero_python.exceptions import AccountingBadRequestException # If specific exceptions handled

logger = logging.getLogger("xero")

class XeroQuoteCreator(XeroDocumentCreator):
    """
    Handles Quote creation in Xero.
    """
    def __init__(self, client, job):
        """
        Initializes the quote creator. Both client and job are required for quotes.
        Calls the base class __init__ ensuring consistent signature.
        """
        if not client or not job:
             raise ValueError("Client and Job are required for XeroQuoteCreator")
        # Call the base class __init__ with the client and the job
        super().__init__(client=client, job=job)

    def get_xero_id(self):
        # self.job is guaranteed to exist here due to the __init__ check
        return str(self.job.quote.xero_id) if hasattr(self.job, "quote") and self.job.quote else None

    def get_xero_update_method(self):
        # For quotes, update/create might be the same endpoint or specific ones
        # Assuming update_or_create_quotes exists and handles setting status to DELETED
        return self.xero_api.update_or_create_quotes

    def get_local_model(self):
        return Quote

    def state_valid_for_xero(self):
        """
        Checks if the job is in a valid state to be quoted in Xero.
        Returns True if valid, False otherwise.
        """
        # self.job is guaranteed to exist here due to the __init__ check
        return not self.job.quoted

    # --- Methods moved from the misplaced block ---

    def validate_job(self):
        """
        Ensures the job is valid for quote creation.
        (This seems redundant now with state_valid_for_xero, consider removing/merging)
        """
        if self.job.quoted:
            raise ValueError(f"Job {self.job.id} is already quoted.")

    def get_line_items(self):
        """
        Generate quote-specific LineItems.
        """
        # Ensure job and pricing exist
        if not self.job or not hasattr(self.job, 'latest_quote_pricing') or not self.job.latest_quote_pricing:
             raise ValueError(f"Job {self.job.id if self.job else 'Unknown'} is missing quote pricing information.")

        line_items = [
            LineItem(
                description=f"Quote for job: {self.job.job_number}{(" - " + self.job.description) if self.job.description else ''}",
                quantity=1,
                unit_amount=float(self.job.latest_quote_pricing.total_revenue) or 0.00,
                # Assuming account code 200 is correct for quotes
                account_code="200",
            )
        ]
        return line_items

    def get_xero_document(self, type: str) -> XeroQuote:
        """
        Creates a quote object for Xero creation or deletion.
        """
        # Ensure job exists before accessing attributes
        if not self.job:
            raise ValueError("Job is required to get Xero document for a quote.")

        match (type):
            case "create":
                # Use job.client which is guaranteed by __init__
                contact = self.get_xero_contact()
                line_items = self.get_line_items()
                base_data = {
                    "contact": contact,
                    "line_items": line_items,
                    "date": format_date(timezone.now()),
                    "expiry_date": format_date(timezone.now() + timedelta(days=30)),
                    "line_amount_types": "Exclusive", # Assuming Exclusive
                    "currency_code": "NZD", # Assuming NZD
                    "status": "DRAFT",
                }
                # Add reference only if job has an order_number
                if hasattr(self.job, 'order_number') and self.job.order_number:
                    base_data["reference"] = self.job.order_number

                return XeroQuote(**base_data)

            case "delete":
                xero_id = self.get_xero_id()
                if not xero_id:
                    raise ValueError("Cannot delete quote without a Xero ID.")
                # Deletion typically involves setting status to DELETED via an update call
                return XeroQuote(
                    quote_id=xero_id,
                    status="DELETED",
                    # Other fields might be required by Xero API for update/delete status change
                    # contact=self.get_xero_contact(), # Likely not needed for delete status change
                    # line_items=self.get_line_items(), # Likely not needed for delete status
                    # date=format_date(timezone.now()), # Likely not needed for delete status
                )
            case _:
                 raise ValueError(f"Unknown document type for Quote: {type}")


    def create_document(self):
        """Creates a quote, processes response, stores locally and returns the quote URL."""
        # Calls the base class create_document to handle API call
        response = super().create_document()

        if response and response.quotes:
            xero_quote_data = response.quotes[0]
            xero_quote_id = getattr(xero_quote_data, 'quote_id', None)
            if not xero_quote_id:
                 logger.error("Xero response missing quote_id.")
                 raise ValueError("Xero response missing quote_id.")

            quote_url = f"https://go.xero.com/app/quotes/edit/{xero_quote_id}"

            # Create local Quote record
            quote = Quote.objects.create(
                xero_id=xero_quote_id,
                job=self.job,
                client=self.client,
                date=timezone.now().date(),
                status=QuoteStatus.DRAFT, # Set local status
                total_excl_tax=Decimal(getattr(xero_quote_data, 'sub_total', 0)),
                total_incl_tax=Decimal(getattr(xero_quote_data, 'total', 0)),
                xero_last_modified=timezone.now(), # Use current time as approximation
                xero_last_synced=timezone.now(),
                online_url=quote_url,
                # Store raw response for debugging
                raw_json=json.dumps(xero_quote_data.to_dict(), default=str),
            )

            logger.info(f"Quote {quote.id} created successfully for job {self.job.id}")

            # Return success details for the view
            return JsonResponse(
                {
                    "success": True,
                    "xero_id": str(xero_quote_id),
                    "client": self.client.name,
                    "quote_url": quote_url,
                }
            )
        else:
            # Handle API failure or unexpected response
            error_msg = "No quotes found in the Xero response or failed to create quote."
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
        """Deletes a quote in Xero and locally."""
        # Calls the base class delete_document which handles the API call
        response = super().delete_document()

        if response and response.quotes:
             # Check if the response indicates successful deletion (e.g., status is DELETED)
             # Note: Xero API might just return the updated object with DELETED status
             xero_quote_data = response.quotes[0]
             if str(getattr(xero_quote_data, 'status', '')).upper() == 'DELETED':
                 # Delete local record only after confirming Xero deletion/update
                 if hasattr(self.job, 'quote') and self.job.quote:
                     local_quote_id = self.job.quote.id
                     self.job.quote.delete()
                     logger.info(f"Quote {local_quote_id} deleted successfully for job {self.job.id}")
                 else:
                      logger.warning(f"No local quote found for job {self.job.id} to delete.")
                 return JsonResponse({"success": True})
             else:
                  error_msg = "Xero response did not confirm quote deletion."
                  logger.error(f"{error_msg} Status: {getattr(xero_quote_data, 'status', 'Unknown')}")
                  return JsonResponse({"success": False, "error": error_msg}, status=400)
        else:
            error_msg = "No quotes found in the Xero response or failed to delete quote."
            logger.error(error_msg)
            return JsonResponse({"success": False, "error": error_msg}, status=400)