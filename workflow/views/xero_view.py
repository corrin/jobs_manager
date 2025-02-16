import json
import logging
import re
import traceback
import uuid
from abc import ABC, abstractmethod
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib import messages

from xero_python.accounting import AccountingApi
from xero_python.accounting.models import Contact
from xero_python.accounting.models import Invoice as XeroInvoice
from xero_python.accounting.models import LineItem
from xero_python.accounting.models import Quote as XeroQuote

from workflow.api.xero.sync import synchronise_xero_data
from workflow.api.xero.xero import (
    api_client,
    exchange_code_for_token,
    get_authentication_url,
    get_tenant_id,
    get_tenant_id_from_connections,
    get_token,
    get_valid_token,
    refresh_token,
)
from workflow.enums import InvoiceStatus, QuoteStatus
from workflow.models import Invoice, Job
from workflow.models.quote import Quote
from workflow.utils import extract_messages

logger = logging.getLogger("xero")


# Xero Authentication (Step 1: Redirect user to Xero OAuth2 login)
def xero_authenticate(request: HttpRequest) -> HttpResponse:
    state = str(uuid.uuid4())
    request.session["oauth_state"] = state

    redirect_after_login = request.GET.get("next", "/")
    request.session["post_login_redirect"] = redirect_after_login

    authorization_url = get_authentication_url(state)
    return redirect(authorization_url)


# OAuth callback
def xero_oauth_callback(request: HttpRequest) -> HttpResponse:
    code = request.GET.get("code")
    state = request.GET.get("state")
    session_state = request.session.get("oauth_state")

    result = exchange_code_for_token(code, state, session_state)

    if "error" in result:
        return render(
            request, "xero/error_xero_auth.html", {"error_message": result["error"]}
        )

    redirect_url = request.session.pop("post_login_redirect", "/")
    return redirect(redirect_url)


# Refresh OAuth token and handle redirects
def refresh_xero_token(request: HttpRequest) -> HttpResponse:
    refreshed_token = refresh_token()

    if not refreshed_token:
        return redirect("xero_authenticate")

    return redirect("xero_get_contacts")


# Xero connection success view
def success_xero_connection(request: HttpRequest) -> HttpResponse:
    return render(request, "xero/success_xero_connection.html")


def refresh_xero_data(request):
    try:
        token = get_token()

        if not token:
            logger.info(
                "User is not authenticated with Xero, redirecting to authentication"
            )
            return redirect(
                "authenticate_xero"
            )  # Redirect to the Xero authentication path

        # If authenticated, proceed with syncing data
        synchronise_xero_data()
        logger.info("Xero data successfully refreshed")

    except Exception as e:
        if "token" in str(e).lower():  # Or check for the specific error code
            logger.error(f"Error while refreshing Xero data: {str(e)}")
            return redirect("authenticate_xero")
        else:
            logger.error(f"Error while refreshing Xero data: {str(e)}")
            traceback.print_exc()
            return render(
                request, "general/generic_error.html", {"error_message": str(e)}
            )

    # After successful sync, redirect to the home page or wherever appropriate
    return redirect("/")


def clean_payload(payload):
    """Remove null fields from payload."""
    if isinstance(payload, dict):
        return {k: clean_payload(v) for k, v in payload.items() if v is not None}
    if isinstance(payload, list):
        return [clean_payload(v) for v in payload if v is not None]
    return payload


def format_date(dt):
    return dt.strftime("%Y-%m-%d")


def convert_to_pascal_case(obj):
    """
    Recursively converts dictionary keys from snake_case to PascalCase.
    """
    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            pascal_key = re.sub(r"(?:^|_)(.)", lambda x: x.group(1).upper(), key)
            new_dict[pascal_key] = convert_to_pascal_case(value)
        return new_dict
    elif isinstance(obj, list):
        return [convert_to_pascal_case(item) for item in obj]
    else:
        return obj


class XeroDocumentCreator(ABC):
    """
    Base class for creating Xero Documents (Invoices, Quotes, Contacts).
    Implements common logic and provides abstract methods for customization.
    """

    def __init__(self, job):
        self.job = job
        self.client = job.client
        self.xero_api = AccountingApi(api_client)
        self.xero_tenant_id = get_tenant_id()

    @abstractmethod
    def get_xero_id(self):
        """
        Returns the Xero ID for the document.
        """
        pass

    @abstractmethod
    def validate_job(self):
        """
        Ensures the job is valid for Xero document creation.
        This is, if the job is already invoiced or quoted, then another document shouldn't be created.
        """
        pass

    @abstractmethod
    def get_line_items(self):
        """
        Returns a list of LineItem objects for the document
        """
        pass

    @abstractmethod
    def get_xero_document(self, type):
        """
        Returns a XeroDocument object for the document
        """
        pass

    @abstractmethod
    def get_local_model(self):
        """
        Returns the local model for the document
        """
        pass

    @abstractmethod
    def get_xero_update_method(self):
        """
        Returns the update method for the document
        """
        pass

    def validate_client(self):
        """
        Ensures the client exists and is synced with Xero
        """
        if not self.client:
            raise ValueError("Job does not have a client")
        if not self.client.validate_for_xero():
            raise ValueError("Client data is not valid for Xero")
        if not self.client.xero_contact_id:
            raise ValueError(
                f"Client {self.client.name} does not have a valid Xero contact ID. Sync the client with Xero first."
            )

    def get_xero_contact(self):
        """
        Returns a Xero Contact object for the client
        """
        return Contact(contact_id=self.client.xero_contact_id, name=self.client.name)

    def create_document(self):
        """
        Handles document creation and API communication with Xero.
        """
        self.validate_client()
        self.validate_job()

        xero_document = self.get_xero_document(type="create")

        try:
            # Convert to PascalCase to match XeroAPI required format and clean payload
            payload = convert_to_pascal_case(clean_payload(xero_document.to_dict()))
            logger.debug(f"Serialized payload: {json.dumps(payload, indent=4)}")
        except Exception as e:
            logger.error(f"Error serializing XeroDocument: {str(e)}")
            raise

        try:
            if isinstance(self, XeroInvoiceCreator):
                response, http_status, http_headers = self.xero_api.create_invoices(
                    self.xero_tenant_id, invoices=payload, _return_http_data_only=False
                )
            elif isinstance(self, XeroQuoteCreator):
                response, http_status, http_headers = self.xero_api.create_quotes(
                    self.xero_tenant_id, quotes=payload, _return_http_data_only=False
                )
            else:
                raise ValueError("Unknown Xero document type.")

            logger.debug(f"Response Content: {response}")
            logger.debug(f"HTTP Status: {http_status}")
            # logger.debug(f"HTTP Headers: {http_headers}")
        except Exception as e:
            logger.error(f"Error sending document to Xero: {str(e)}")
            if hasattr(e, "body"):
                logger.error(f"Response body: {e.body}")
            raise

        return response


class XeroQuoteCreator(XeroDocumentCreator):
    """
    Handles Quote creation in Xero.
    """

    def get_xero_id(self):
        return self.job.quote.xero_id if hasattr(self.job, "quote") else None

    def get_xero_update_method(self):
        return self.xero_api.update_or_create_quotes

    def get_local_model(self):
        return Quote

    def validate_job(self):
        """
        Ensures the job is valid for quote creation.
        """
        if self.job.quoted:
            raise ValueError(f"Job {self.job.id} is already quoted.")

    def get_line_items(self):
        """
        Generate quote-specific LineItems.
        """
        line_items = [
            LineItem(
                description=self.job.description or f"Quote for Job {self.job.name}",
                quantity=1,
                unit_amount=float(self.job.latest_reality_pricing.total_revenue)
                or 0.00,
                account_code=200,
            )
        ]

        return line_items

    def get_xero_document(self, type):
        """
        Creates a quote object for Xero creation or deletion.
        """
        return XeroQuote(
            contact=self.get_xero_contact(),
            line_items=self.get_line_items(),
            date=format_date(timezone.now()),
            expiry_date=format_date(timezone.now() + timedelta(days=30)),
            line_amount_types="Exclusive",
            reference=f"Quote for job {self.job.id}",
            currency_code="NZD",
            status="DRAFT",
        )

    def create_document(self):
        """Creates a quote and returns the quote URL."""
        response = super().create_document()

        if response and response.quotes:
            xero_quote_data = response.quotes[0]
            xero_quote_id = xero_quote_data.quote_id

            quote_url = f"https://go.xero.com/app/quotes/edit/{xero_quote_id}"

            quote = Quote.objects.create(
                xero_id=xero_quote_id,
                job=self.job,
                client=self.client,
                date=timezone.now().date(),
                status=QuoteStatus.DRAFT,
                total_excl_tax=Decimal(xero_quote_data.sub_total),
                total_incl_tax=Decimal(xero_quote_data.total),
                xero_last_modified=timezone.now(),
                xero_last_synced=timezone.now(),
                online_url=quote_url,
                raw_json=json.dumps(response.to_dict(), default=str),
            )

            logger.info(f"Quote {quote.id} created successfully for job {self.job.id}")

            return JsonResponse(
                {
                    "success": True,
                    "xero_id": xero_quote_id,
                    "client": self.client.name,
                    "quote_url": quote_url,
                }
            )
        else:
            logger.error("No quotes found in the response or failed to create quote.")
            return JsonResponse(
                {"success": False, "error": "No quotes found in the response."},
                status=400,
            )


class XeroInvoiceCreator(XeroDocumentCreator):
    """
    Handles invoice creation in Xero.
    """

    def get_line_items(self):
        """
        Generates invoice-specific LineItems.
        """
        description_line_item = (
            LineItem(description=self.job.description) if self.job.description else None
        )

        xero_line_items = [
            LineItem(
                description="Price as quoted",
                quantity=1,
                unit_amount=float(self.job.latest_reality_pricing.total_revenue)
                or 0.00,
                account_code=200,
            )
        ]

        if description_line_item:
            xero_line_items.append(description_line_item)

        return xero_line_items

    def get_xero_document(self):
        """
        Creates an invoice object for Xero.
        """
        return XeroInvoice(
            type="ACCREC",
            contact=self.get_xero_contact(),
            line_items=self.get_line_items(),
            date=format_date(timezone.now()),
            due_date=format_date(timezone.now() + timedelta(days=30)),
            line_amount_types="Exclusive",
            reference=f"Invoice for job {self.job.id}",
            currency_code="NZD",
            status="DRAFT",
        )

    def create_document(self):
        """Creates an invoice, processes response, and stores it in the database."""
        response = super().create_document()

        if response and response.invoices:
            xero_invoice_data = response.invoices[0]
            xero_invoice_id = xero_invoice_data.invoice_id

            invoice_url = f"https://invoicing.xero.com/edit/{xero_invoice_id}"

            invoice_json = json.dumps(response.to_dict(), default=str)

            invoice = Invoice.objects.create(
                xero_id=xero_invoice_id,
                job=self.job,
                client=self.client,
                number=xero_invoice_data.invoice_number,
                date=timezone.now().date(),
                due_date=(timezone.now().date() + timedelta(days=30)),
                status=InvoiceStatus.SUBMITTED,
                total_excl_tax=Decimal(xero_invoice_data.total),
                tax=Decimal(xero_invoice_data.total_tax),
                total_incl_tax=Decimal(xero_invoice_data.total)
                + Decimal(xero_invoice_data.total_tax),
                amount_due=Decimal(xero_invoice_data.amount_due),
                xero_last_synced=timezone.now(),
                xero_last_modified=timezone.now(),
                online_url=invoice_url,
                raw_json=invoice_json,
            )

            logger.info(
                f"Invoice {invoice.id} created successfully for job {self.job.id}"
            )

            return JsonResponse(
                {
                    "success": True,
                    "invoice_id": invoice.id,
                    "xero_id": xero_invoice_id,
                    "client": invoice.client.name,
                    "total_excl_tax": str(invoice.total_excl_tax),
                    "total_incl_tax": str(invoice.total_incl_tax),
                    "invoice_url": invoice_url,
                }
            )
        else:
            logger.error(
                "No invoices found in the response or failed to update invoice."
            )
            return JsonResponse(
                {"success": False, "error": "No invoices found in the response."},
                status=400,
            )


def ensure_xero_authentication():
    """
    Ensure the user is authenticated with Xero and retrieves the tenand ID.
    If authentication is missing, it returns a JSON response prompting login.
    """
    token = get_valid_token()
    if not token:
        return JsonResponse(
            {
                "success": False,
                "redirect_to_auth": True,
                "message": "Your Xero session has expired. Please log in again.",
            },
            status=401,
        )

    tenant_id = cache.get("tenant_id")
    if not tenant_id:
        try:
            tenant_id = get_tenant_id_from_connections()
            cache.set("xero_tenant_id", tenant_id, timeout=1800)
        except Exception as e:
            logger.error(f"Error retrieving tenant ID: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "redirect_to_auth": True,
                    "message": "Unable to fetch Xero tenant ID. Please log in Xero again.",
                },
                status=401,
            )
    return tenant_id


def create_xero_invoice(request, job_id):
    """
    Creates an Invoice in Xero for a given job.
    """
    tenant_id = ensure_xero_authentication()
    if isinstance(
        tenant_id, JsonResponse
    ):  # If the tenant ID is an error message, return it directly
        return tenant_id

    try:
        job = Job.objects.get(id=job_id)
        creator = XeroInvoiceCreator(job)
        response = json.loads(creator.create_document().content.decode())

        if not response.get("success"):
            messages.error(
                request, f"Failed to create invoice: {response.get('error')}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": response.get("error"),
                    "messages": extract_messages(request),
                }
            )

        messages.success(request, "Invoice created successfully")
        return JsonResponse(
            {
                "success": True,
                "xero_id": response.get("xero_id"),
                "client": response.get("client"),
                "total_excl_tax": response.get("total_excl_tax"),
                "total_incl_tax": response.get("total_incl_tax"),
                "invoice_url": response.get("invoice_url"),
                "messages": extract_messages(request),
            }
        )

    except Exception as e:
        logger.error(f"Error in create_invoice_job: {str(e)}")
        messages.error(request, "An error occurred while creating the invoice")
        return JsonResponse(
            {"success": False, "messages": extract_messages(request)}, status=500
        )


def create_xero_quote(request, job_id):
    """
    Creates a quote in Xero for a given job.
    """
    tenant_id = ensure_xero_authentication()
    if isinstance(
        tenant_id, JsonResponse
    ):  # If the tenant ID is an error message, return it directly
        return tenant_id

    try:
        job = Job.objects.get(id=job_id)
        creator = XeroQuoteCreator(job)
        response = json.loads(creator.create_document().content.decode())

        if not response.get("success"):
            messages.error(request, f"Failed to create quote: {response.get('error')}")
            return JsonResponse(
                {
                    "success": False,
                    "error": response.get("error"),
                    "messages": extract_messages(request),
                }
            )

    except Exception as e:
        logger.error(f"Error in create_xero_quote: {str(e)}")
        messages.error(request, f"An error occurred while creating the quote: {str(e)}")
        return JsonResponse(
            {"success": False, "messages": extract_messages(request)}, status=500
        )


def delete_xero_invoice(request, job_id):
    """
    Deletes an invoice in Xero for a given job.
    """
    tenant_id = ensure_xero_authentication()
    if isinstance(
        tenant_id, JsonResponse
    ):  # If the tenant ID is an error message, return it directly
        return tenant_id

    try:
        job = Job.objects.get(id=job_id)
        creator = XeroInvoiceCreator(job)
        response = json.loads(creator.delete_document().content.decode())

        if not response.get("success"):
            messages.error(
                request, f"Failed to delete invoice: {response.get("error")}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": response.get("error"),
                    "messages": extract_messages(request),
                },
                status=400,
            )

        messages.success(request, "Invoice deleted successfully")
        return JsonResponse({"success": True, "messages": extract_messages(request)})

    except Exception as e:
        logger.error(f"Error in delete_xero_invoice: {str(e)}")
        messages.error(
            request, f"An error occurred while deleting the invoice: {str(e)}"
        )
        return JsonResponse(
            {"success": False, "messages": extract_messages(request)}, status=500
        )


def xero_disconnect(request):
    """
    Disconnects from Xero by clearing the token from cache.
    """
    try:
        cache.delete('xero_token')
        cache.delete('xero_tenant_id')
        messages.success(request, "Successfully disconnected from Xero")
    except Exception as e:
        logger.error(f"Error disconnecting from Xero: {str(e)}")
        messages.error(request, "Failed to disconnect from Xero")
    
    return redirect("/")


def delete_xero_quote(request, job_id):
    """
    Deletes a quote in Xero for a given job.
    """
    tenant_id = ensure_xero_authentication()
    if isinstance(
        tenant_id, JsonResponse
    ):  # If the tenant ID is an error message, return it directly
        return tenant_id

    try:
        job = Job.objects.get(id=job_id)
        creator = XeroQuoteCreator(job)
        response = json.loads(creator.delete_document().content.decode())
        if not response.get("success"):
            logger.error(f"Failed to delete quote: {response.get("error")}")
            messages.error(request, f"Failed to delete quote: {response.get("error")}")
            return JsonResponse(
                {"success": True, "messages": extract_messages(request)}
            )
        messages.success(request, "Quote deleted successfully")
        return JsonResponse({"success": True, "messages": extract_messages(request)})
    except Exception as e:
        logger.error(f"Error in delete_xero_quote: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


class XeroIndexView(TemplateView):
    """Note this page is currently inaccessible.  We are using a dropdown menu instead.
    Kept as of 2025-01-07 in case we change our mind"""

    template_name = "xero_index.html"
