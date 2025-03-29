# workflow/views/xero_po_creator.py
import logging
import json
from decimal import Decimal

from django.http import JsonResponse
from django.utils import timezone

# Import base class and helpers
from .xero_base_creator import XeroDocumentCreator
from .xero_helpers import format_date, clean_payload, convert_to_pascal_case

# Import models
from workflow.models import PurchaseOrder, XeroAccount, Client, Job # Add models used
from xero_python.accounting.models import LineItem, PurchaseOrder as XeroPurchaseOrder
from xero_python.exceptions import AccountingBadRequestException

logger = logging.getLogger("xero")

class XeroPurchaseOrderCreator(XeroDocumentCreator):
    """
    Handles Purchase Order creation and updates in Xero.
    """

    purchase_order: PurchaseOrder | None = None

    def __init__(self, purchase_order: PurchaseOrder):
        """Initializes the purchase order creator."""
        if not purchase_order or not purchase_order.supplier:
            raise ValueError("PurchaseOrder and associated Supplier are required.")
        client = purchase_order.supplier
        # Call the base class __init__ with the client and job=None
        super().__init__(client=client, job=None)
        # Set the purchase_order specific attribute
        self.purchase_order = purchase_order
        # Note: self.client and self.job are now set by the super().__init__ call
        # Note: self.xero_api and self.xero_tenant_id are also set by super().__init__
        # self.xero_tenant_id = get_tenant_id() # Already set in base __init__

    def get_xero_id(self) -> str | None:
        """Returns the Xero ID if the local PO has one."""
        return str(self.purchase_order.xero_id) if self.purchase_order and self.purchase_order.xero_id else None

    def get_xero_update_method(self):
        """Returns the Xero API method for creating/updating POs."""
        # This method handles both create and update (PUT/POST)
        return self.xero_api.update_or_create_purchase_orders

    def get_local_model(self):
        """Returns the local Django model class."""
        return PurchaseOrder

    def state_valid_for_xero(self) -> bool:
        """
        Checks if the purchase order is in 'draft' status for initial sending.
        Updates might be possible in other statuses depending on Xero rules.
        """
        # For initial creation/sending, we often require 'draft'
        return self.purchase_order.status == 'draft'

    def get_line_items(self) -> list[LineItem]:
        """
        Generates purchase order-specific LineItems for the Xero API payload.
        """
        logger.debug("Starting get_line_items for PO")
        xero_line_items = []
        account_code = None

        # Look up the Purchases account code
        try:
            # Consider making the account name/code configurable
            purchases_account = XeroAccount.objects.get(account_name__iexact="Purchases")
            account_code = purchases_account.account_code
        except XeroAccount.DoesNotExist:
            logger.warning("Could not find 'Purchases' account in Xero accounts, omitting account code for PO lines.")
        except XeroAccount.MultipleObjectsReturned:
            accounts = XeroAccount.objects.filter(account_name__iexact="Purchases")
            logger.warning(f"Found multiple 'Purchases' accounts: {[(a.account_name, a.account_code, a.xero_id) for a in accounts]}. Omitting account code.")
            # Decide if this should raise an error or just warn

        if not self.purchase_order:
             logger.error("Purchase order object is missing in get_line_items.")
             return [] # Or raise error

        for line in self.purchase_order.lines.all():
            # Skip lines marked as 'Price to be confirmed'
            if line.price_tbc or line.unit_cost is None: # Check both just in case
                logger.debug(f"Skipping PO line {line.id} due to TBC price.")
                continue

            description = line.description
            # Prepend Job Number if available
            if line.job:
                description = f"{line.job.job_number} - {description}"

            line_item_data = {
                "description": description,
                "quantity": float(line.quantity),
                "unit_amount": float(line.unit_cost)
            }

            # Add account code only if found
            if account_code:
                line_item_data["account_code"] = account_code

            try:
                 # Append the LineItem object directly
                 xero_line_items.append(LineItem(**line_item_data))
            except Exception as e:
                 logger.error(f"Error creating xero-python LineItem object for PO line {line.id}: {e}", exc_info=True)
                 # Decide whether to skip this line or raise the error

        logger.debug(f"Finished get_line_items for PO. Prepared {len(xero_line_items)} items.")
        return xero_line_items

    def get_xero_document(self, type="create") -> XeroPurchaseOrder:
        """
        Returns a xero_python PurchaseOrder object based on the specified type.
        """
        if not self.purchase_order:
             raise ValueError("PurchaseOrder object is missing.")

        if type == "delete":
            xero_id = self.get_xero_id()
            if not xero_id:
                raise ValueError("Cannot delete a purchase order without a Xero ID.")
            # Deletion via API usually means setting status to DELETED via update
            return XeroPurchaseOrder(
                purchase_order_id=xero_id,
                status="DELETED"
            )
        elif type in ["create", "update"]:
            # Build the common document data dictionary using snake_case keys
            document_data = {
                "purchase_order_number": self.purchase_order.po_number,
                "contact": self.get_xero_contact(), # Uses base class method
                "date": format_date(self.purchase_order.order_date),
                "line_items": self.get_line_items(),
                "status": "SUBMITTED" # TODO: Review if this should always be SUBMITTED or based on local status/action
            }

            # Add optional fields if they exist
            if self.purchase_order.expected_delivery:
                document_data["delivery_date"] = format_date(self.purchase_order.expected_delivery)
            if self.purchase_order.reference:
                document_data["reference"] = self.purchase_order.reference

            # Add the Xero PurchaseOrderID only for updates
            if type == "update":
                xero_id = self.get_xero_id()
                if not xero_id:
                    raise ValueError("Cannot update a purchase order without a Xero ID.")
                document_data["purchase_order_id"] = xero_id

            # Log the data just before creating the XeroPurchaseOrder object
            logger.debug(f"Data for XeroPurchaseOrder init: {document_data}")
            try:
                return XeroPurchaseOrder(**document_data)
            except Exception as e:
                 logger.error(f"Error initializing xero_python PurchaseOrder model: {e}", exc_info=True)
                 raise # Re-raise the error
        else:
            raise ValueError(f"Unknown document type for Purchase Order: {type}")

    def create_document(self):
        """
        Overrides base method to handle purchase order specific creation/update via Xero API.
        Processes the response and updates the local PurchaseOrder record.
        Returns a JsonResponse suitable for the calling view.
        """
        self.validate_client() # From base class

        # Check local state validity - e.g., only send 'draft' POs initially
        if not self.state_valid_for_xero():
            raise ValueError(f"Purchase order {self.purchase_order.id} is not in draft status. Cannot send to Xero.")

        # Determine if we are creating or updating based on existing xero_id
        action_type = "update" if self.get_xero_id() else "create"
        logger.info(f"Attempting to {action_type} purchase order {self.purchase_order.id} in Xero.")

        try:
            # Get the xero-python model object representation
            xero_document = self.get_xero_document(type=action_type)
        except Exception as e:
             logger.error(f"Error preparing Xero document data for PO {self.purchase_order.id}: {e}", exc_info=True)
             # Return JsonResponse directly for the view
             return JsonResponse({"success": False, "error": f"Failed to prepare data: {str(e)}"}, status=500)

        try:
            # Convert to PascalCase, clean payload, and wrap for the API
            payload = convert_to_pascal_case(clean_payload(xero_document.to_dict()))
            # The API expects a list under the "PurchaseOrders" key
            payload_list = {"PurchaseOrders": [payload]}
            logger.debug(f"Serialized payload for {action_type}: {json.dumps(payload_list, indent=4)}")
        except Exception as e:
            logger.error(f"Error serializing XeroDocument for {action_type}: {str(e)}", exc_info=True)
            # Return JsonResponse directly for the view
            return JsonResponse({"success": False, "error": f"Failed to serialize data for Xero: {str(e)}"}, status=500)

        try:
            # Use the appropriate update/create method from the Xero API client
            update_method = self.get_xero_update_method()
            logger.info(f"Calling Xero API method: {update_method.__name__}")
            response, http_status, http_headers = update_method(
                self.xero_tenant_id,
                purchase_orders=payload_list,
                summarize_errors=False, # Get detailed errors if any
                _return_http_data_only=False # Get full response object
            )

            logger.debug(f"Xero API Response Content ({action_type}): {response}")
            logger.debug(f"Xero API HTTP Status ({action_type}): {http_status}")

            # Process the response
            if response and hasattr(response, 'purchase_orders') and response.purchase_orders:
                xero_po_data = response.purchase_orders[0]

                # Check for validation errors returned by Xero
                if hasattr(xero_po_data, 'validation_errors') and xero_po_data.validation_errors:
                    error_details = "; ".join([f"{err.message}" for err in xero_po_data.validation_errors]) # Use err.message
                    logger.error(f"Xero validation errors for PO {self.purchase_order.id}: {error_details}")
                    # Return JsonResponse directly for the view
                    return JsonResponse({"success": False, "error": f"Xero validation errors: {error_details}"}, status=400)

                xero_id = getattr(xero_po_data, 'purchase_order_id', None)
                if not xero_id:
                     logger.error(f"Xero response missing purchase_order_id for PO {self.purchase_order.id}")
                     # Return JsonResponse directly for the view
                     return JsonResponse({"success": False, "error": "Xero response missing purchase order ID"}, status=500)

                # Update local purchase order with Xero ID and mark as submitted
                self.purchase_order.xero_id = xero_id
                self.purchase_order.status = 'submitted' # Mark as submitted locally
                self.purchase_order.xero_last_synced = timezone.now()
                # Consider also updating xero_last_modified based on response.updated_date_utc
                self.purchase_order.save(update_fields=['xero_id', 'status', 'xero_last_synced'])

                logger.info(f"Successfully {action_type}d purchase order {self.purchase_order.id} in Xero (Xero ID: {xero_id}).")

                # Return success response data for the view
                return JsonResponse({
                    "success": True,
                    "xero_id": str(xero_id),
                    "status": self.purchase_order.status, # Return updated local status
                    "action": action_type,
                })
            else:
                # Handle cases where the response structure is unexpected
                error_msg = f"Unexpected or empty response from Xero API during {action_type}."
                logger.error(f"{error_msg} for PO {self.purchase_order.id}. Response: {response}")
                # Return JsonResponse directly for the view
                return JsonResponse({"success": False, "error": error_msg}, status=500)

        except AccountingBadRequestException as e:
             # Handle specific Xero API bad request errors (e.g., validation)
            error_body = {}
            error_message = str(e)
            try:
                 if hasattr(e, 'body') and e.body:
                      error_body = json.loads(e.body)
                      # Try to extract a more specific message
                      error_message = error_body.get('Detail', error_body.get('Message', str(e)))
            except json.JSONDecodeError:
                 logger.warning("Could not decode Xero error body JSON.")

            logger.error(f"Xero API Bad Request during {action_type} for PO {self.purchase_order.id}: {error_message} Body: {error_body}")
            # Return JsonResponse directly for the view
            return JsonResponse({"success": False, "error": f"Xero Error: {error_message}"}, status=e.status)
        except Exception as e:
            # Catch-all for other unexpected errors during API call
            logger.error(f"Unexpected error sending PO {self.purchase_order.id} to Xero ({action_type}): {str(e)}", exc_info=True)
            # Return JsonResponse directly for the view
            return JsonResponse({"success": False, "error": f"An unexpected error occurred: {str(e)}"}, status=500)

# Note: The misplaced Quote methods that were here previously have been removed.