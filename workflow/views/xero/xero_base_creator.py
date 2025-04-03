# workflow/views/xero_base_creator.py
import logging
import json
from abc import ABC, abstractmethod
from typing import Any

from django.http import JsonResponse

from xero_python.accounting import AccountingApi
from xero_python.accounting.models import Contact

# Import models used in type hints or logic
from workflow.models import Job, Client
from workflow.api.xero.xero import api_client, get_tenant_id
from .xero_helpers import clean_payload, convert_to_pascal_case # Import helpers

logger = logging.getLogger("xero")

class XeroDocumentCreator(ABC):
    """
    Base class for creating Xero Documents (Invoices, Quotes, Purchase Orders).
    Implements common logic and provides abstract methods for customization.
    """

    job: Job | None # Job is optional now
    client: Client
    xero_api: AccountingApi
    xero_tenant_id: str

    def __init__(self, client, job=None):
        """
        Initializes the creator.

        Args:
            client (Client): The client or supplier associated with the document.
            job (Job, optional): The associated job. Defaults to None.
                                 Required for document types like Invoice/Quote.
                                 Not directly used for PurchaseOrder at this level.
        """
        if client is None:
             raise ValueError("Client cannot be None for XeroDocumentCreator")
        self.client = client
        self.job = job # Optional job association
        self.xero_api = AccountingApi(api_client)
        self.xero_tenant_id = get_tenant_id()

    @abstractmethod
    def get_xero_id(self) -> str | None:
        """
        Returns the Xero ID for the document if it exists locally.
        """
        pass

    @abstractmethod
    def state_valid_for_xero(self) -> bool:
        """
        Checks if the document is in a valid state to be sent to Xero.
        Returns True if valid, False otherwise.
        """
        pass

    @abstractmethod
    def get_line_items(self) -> list:
        """
        Returns a list of xero_python LineItem objects for the document.
        """
        pass

    @abstractmethod
    def get_xero_document(self, type: str) -> Any:
        """
        Returns a xero_python document model object (e.g., XeroInvoice, XeroQuote).
        """
        pass

    @abstractmethod
    def get_local_model(self) -> Any:
        """
        Returns the local Django model class for the document (e.g., Invoice, Quote).
        """
        pass

    @abstractmethod
    def get_xero_update_method(self) -> Any:
        """
        Returns the appropriate Xero API method for updating/creating the document
        (e.g., self.xero_api.update_or_create_invoices).
        """
        pass

    def validate_client(self):
        """
        Ensures the client exists and is synced with Xero.
        """
        if not self.client:
            # This check might be redundant now client is required in __init__
            raise ValueError("Client is missing")
        if not self.client.validate_for_xero():
            raise ValueError("Client data is not valid for Xero")
        if not self.client.xero_contact_id:
            raise ValueError(
                f"Client {self.client.name} does not have a valid Xero contact ID. Sync the client with Xero first."
            )

    def get_xero_contact(self) -> Contact:
        """
        Returns a Xero Contact object for the client.
        """
        return Contact(contact_id=self.client.xero_contact_id, name=self.client.name)

    def create_document(self):
        """
        Handles document creation and API communication with Xero.
        This method prepares the payload and calls the appropriate Xero API endpoint.
        Subclasses might override this for more specific response handling.
        """
        # Log the type of 'self' when this method is entered
        logger.info(f"Base create_document called with self type: {type(self)}")
        self.validate_client()

        if not self.state_valid_for_xero():
            raise ValueError(f"Document is not in a valid state for Xero submission.")

        # Use 'create' type for initial creation attempt
        xero_document = self.get_xero_document(type="create")

        try:
            # Convert to PascalCase to match XeroAPI required format and clean payload
            # Note: xero-python library expects snake_case for model init,
            # but the API call itself needs PascalCase. The library handles this,
            # but we apply conversion here before wrapping for the final API call structure.
            payload = convert_to_pascal_case(clean_payload(xero_document.to_dict()))
            logger.debug(f"Raw payload dictionary: {payload}")

            # Determine the correct payload structure for the API call
            # This depends on the specific endpoint (Invoices, Quotes, PurchaseOrders)
            # We need to import the specific creator types here eventually
            # Defer imports to avoid circular dependencies until files are created
            from .xero_invoice_creator import XeroInvoiceCreator
            from .xero_quote_creator import XeroQuoteCreator
            from .xero_po_creator import XeroPurchaseOrderCreator

            if isinstance(self, XeroInvoiceCreator):
                api_payload = {"Invoices": [payload]}
                api_method = self.xero_api.create_invoices
                kwargs = {'invoices': api_payload}
            elif isinstance(self, XeroQuoteCreator):
                api_payload = {"Quotes": [payload]}
                api_method = self.xero_api.create_quotes
                kwargs = {'quotes': api_payload}
            elif isinstance(self, XeroPurchaseOrderCreator):
                api_payload = {"PurchaseOrders": [payload]}
                api_method = self.xero_api.create_purchase_orders
                kwargs = {'purchase_orders': api_payload}
            else:
                raise ValueError("Unknown Xero document type for API payload structure.")

            logger.debug(f"Final API payload: {json.dumps(api_payload, indent=4)}")

        except Exception as e:
            logger.error(f"Error preparing payload for XeroDocument: {str(e)}", exc_info=True)
            raise # Re-raise after logging

        try:
            logger.info(f"Attempting to call Xero API method: {api_method.__name__}")
            response, http_status, http_headers = api_method(
                self.xero_tenant_id, **kwargs, _return_http_data_only=False
            )

            logger.debug(f"Xero API Response Content: {response}")
            logger.debug(f"Xero API HTTP Status: {http_status}")
            # logger.debug(f"HTTP Headers: {http_headers}")

        except Exception as e:
            # Log details before re-raising or handling in subclass
            logger.error(f"Error calling Xero API method {api_method.__name__}: {str(e)}")
            if hasattr(e, "body"):
                logger.error(f"Xero API Response body: {e.body}")
            raise # Re-raise for specific handling in view or subclass

        return response # Return the raw xero-python response object

    def delete_document(self):
        """
        Handles document deletion and API communication with Xero.
        Requires subclasses to implement get_xero_update_method appropriately
        (e.g., returning self.xero_api.update_or_create_invoices for setting status to DELETED).
        """
        self.validate_client()
        # Get the document representation needed for deletion (usually includes ID and status=DELETED)
        xero_document = self.get_xero_document(type="delete")

        try:
            payload = convert_to_pascal_case(clean_payload(xero_document.to_dict()))
            logger.debug(f"Serialized payload for delete: {json.dumps(payload, indent=4)}")

            # Determine the correct payload structure for the API call (similar to create)
            # Defer imports to avoid circular dependencies until files are created
            from .xero_invoice_creator import XeroInvoiceCreator
            from .xero_quote_creator import XeroQuoteCreator
            from .xero_po_creator import XeroPurchaseOrderCreator

            if isinstance(self, XeroInvoiceCreator):
                api_payload = {"Invoices": [payload]}
                # Deletion is often handled by POST/PUT with status=DELETED
                api_method = self.get_xero_update_method()
                kwargs = {'invoices': api_payload}
            elif isinstance(self, XeroQuoteCreator):
                api_payload = {"Quotes": [payload]}
                api_method = self.get_xero_update_method()
                kwargs = {'quotes': api_payload}
            elif isinstance(self, XeroPurchaseOrderCreator):
                api_payload = {"PurchaseOrders": [payload]}
                api_method = self.get_xero_update_method()
                kwargs = {'purchase_orders': api_payload}
            else:
                raise ValueError("Unknown Xero document type for delete payload structure.")

        except Exception as e:
            logger.error(f"Error preparing payload for Xero document deletion: {str(e)}", exc_info=True)
            raise

        try:
            logger.info(f"Attempting to call Xero API method for delete: {api_method.__name__}")
            response, http_status, http_headers = api_method(
                self.xero_tenant_id, **kwargs, _return_http_data_only=False
            )

            logger.debug(f"Xero API Delete Response Content: {response}")
            logger.debug(f"Xero API Delete HTTP Status: {http_status}")

        except Exception as e:
            logger.error(f"Error calling Xero API method {api_method.__name__} for delete: {str(e)}")
            if hasattr(e, "body"):
                logger.error(f"Xero API Delete Response body: {e.body}")
            raise

        return response