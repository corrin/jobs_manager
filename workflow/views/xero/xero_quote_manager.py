# workflow/views/xero_quote_creator.py
import logging
import json
from decimal import Decimal
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone

# Import base class and helpers
from .xero_base_manager import XeroDocumentManager
from .xero_helpers import format_date # Assuming format_date is needed

# Import models
from workflow.models import Quote, Client
from job.models import Job
from workflow.enums import QuoteStatus
from xero_python.accounting.models import LineItem, Quote as XeroQuote
from xero_python.exceptions import AccountingBadRequestException, ApiException # If specific exceptions handled

logger = logging.getLogger("xero")

class XeroQuoteManager(XeroDocumentManager):
    """
    Handles Quote creation and syncing in Xero.
    """
    _is_quote_manager = True
    
    def __init__(self, client, job):
        """
        Initializes the quote creator. Both client and job are required for quotes.
        Calls the base class __init__ ensuring consistent signature.
        """
        if not client or not job:
             raise ValueError("Client and Job are required for XeroQuoteManager")
        # Call the base class __init__ with the client and the job
        super().__init__(client=client, job=job)

    def get_xero_id(self):
        # self.job is guaranteed to exist here due to the __init__ check
        return str(self.job.quote.xero_id) if hasattr(self.job, "quote") and self.job.quote else None

    def _get_xero_update_method(self):
        # For quotes, update/create might be the same endpoint or specific ones
        # Assuming update_or_create_quotes exists and handles setting status to DELETED
        return self.xero_api.update_or_create_quotes

    def _get_local_model(self):
        return Quote

    def state_valid_for_xero(self):
        """
        Checks if the job is in a valid state to be quoted in Xero.
        Returns True if valid, False otherwise.
        """
        # self.job is guaranteed to exist here due to the __init__ check
        return not self.job.quoted

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
                # Xero requires a description for quote line items, so we'll have to keep the placeholder in case there's no job description
                description=f"Quote for job: {self.job.job_number}{(" - " + self.job.description) if self.job.description else ''}",
                quantity=1,
                unit_amount=float(self.job.latest_quote_pricing.total_revenue) or 0.00,
                account_code=self._get_account_code(),
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
                    contact=self.get_xero_contact(), # Contact is needed.
                    date=format_date(timezone.now()), # Date is needed.
                )
            case _:
                 raise ValueError(f"Unknown document type for Quote: {type}")


    def create_document(self):
        """Creates a quote, processes response, stores locally and returns the quote URL."""
        try:
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
                    {"success": False, "message": error_msg},
                    status=400, 
                )
        except AccountingBadRequestException as e:
            logger.error(f"Xero API BadRequest during quote creation for job {self.job.id if self.job else 'Unknown'}: {e.status} - {e.reason}", exc_info=True)
            error_message = f"Xero Error ({e.status}): {e.reason}"
            try:
                if e.body:
                    error_body = json.loads(e.body)
                    if "Message" in error_body:
                        error_message = error_body["Message"]
                    elif "Elements" in error_body and error_body.get("Elements") and isinstance(error_body["Elements"], list) and len(error_body["Elements"]) > 0:
                        element = error_body["Elements"][0]
                        if "ValidationErrors" in element and element.get("ValidationErrors") and isinstance(element["ValidationErrors"], list) and len(element["ValidationErrors"]) > 0:
                            error_message = element["ValidationErrors"][0].get("Message", error_message)
                        elif "Message" in element:
                            error_message = element.get("Message", error_message)
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as parse_error:
                logger.error(f"Could not parse detailed error from Xero BadRequestException body for quote: {parse_error}. Body: {e.body}")
            return JsonResponse({"success": False, "message": error_message}, status=e.status)
        except ApiException as e:
            logger.error(f"Xero API Exception during quote creation for job {self.job.id if self.job else 'Unknown'}: {e.status} - {e.reason}", exc_info=True)
            return JsonResponse({"success": False, "message": f"Xero API Error: {e.reason}"}, status=e.status)
        except Exception as e:
            logger.exception(f"Unexpected error during quote creation for job {self.job.id if self.job else 'Unknown'}")
            return JsonResponse({"success": False, "message": "An unexpected error occurred while creating the quote with Xero."}, status=500)

    def delete_document(self):
        """Deletes a quote in Xero and locally."""
        try:
            # Calls the base class delete_document which handles the API call
            response = super().delete_document()

            if not response or not response.quotes:
                error_msg = "No quotes found in the Xero response or failed to delete quote."
                logger.error(error_msg)
                return JsonResponse({"success": False, "message": error_msg}, status=400) # Changed "error" to "message"
            
            xero_quote_data = response.quotes[0]
            status = getattr(xero_quote_data, 'status', None)

            is_deleted = False
            if hasattr(status, 'value'):
                is_deleted = status.value == 'DELETED'
            else:
                is_deleted = str(status).upper() == 'DELETED'
            
            if not is_deleted:
                error_msg = "Xero response did not confirm quote deletion."
                logger.error(f"{error_msg} Status: {status}")
                return JsonResponse({"success": False, "message": error_msg}, status=400) # Changed "error" to "message"
            
            if not hasattr(self.job, 'quote') or not self.job.quote:
                logger.warning(f"No local quote found for job {self.job.id} to delete.")
                # Still return success as Xero operation might have succeeded or there was nothing to delete locally
                return JsonResponse({"success": True, "messages": [{"level": "info", "message": "No local quote to delete, Xero operation may have succeeded."}]})
                
            local_quote_id = self.job.quote.id
            self.job.quote.delete()
            logger.info(f"Quote {local_quote_id} deleted successfully for job {self.job.id}")

            return JsonResponse({"success": True, "messages": [{"level": "success", "message": "Quote deleted successfully."}]})
        except AccountingBadRequestException as e:
            logger.error(f"Xero API BadRequest during quote deletion for job {self.job.id if self.job else 'Unknown'}: {e.status} - {e.reason}", exc_info=True)
            error_message = f"Xero Error ({e.status}): {e.reason}"
            try:
                if e.body:
                    error_body = json.loads(e.body)
                    if "Message" in error_body:
                        error_message = error_body["Message"]
            except (json.JSONDecodeError, KeyError, TypeError) as parse_error:
                logger.error(f"Could not parse detailed error from Xero BadRequestException body for quote deletion: {parse_error}. Body: {e.body}")
            return JsonResponse({"success": False, "message": error_message}, status=e.status)
        except ApiException as e:
            logger.error(f"Xero API Exception during quote deletion for job {self.job.id if self.job else 'Unknown'}: {e.status} - {e.reason}", exc_info=True)
            return JsonResponse({"success": False, "message": f"Xero API Error: {e.reason}"}, status=e.status)
        except Exception as e:
            logger.exception(f"Unexpected error during quote deletion for job {self.job.id if self.job else 'Unknown'}")
            return JsonResponse({"success": False, "message": "An unexpected error occurred while deleting the quote with Xero."}, status=500)
