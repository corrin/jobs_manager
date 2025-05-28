# workflow/views/xero_view.py
import json
import logging
import re # Keep re if used elsewhere, otherwise remove
import traceback
import threading
import uuid
import time
# from abc import ABC, abstractmethod # No longer needed here
from datetime import timedelta, timezone, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import transaction

# Remove direct imports of Xero models if only used in creators
# from xero_python.accounting import AccountingApi
# from xero_python.accounting.models import Contact
# from xero_python.accounting.models import Invoice as XeroInvoice
# from xero_python.accounting.models import LineItem
# from xero_python.accounting.models import Quote as XeroQuote
# from xero_python.accounting.models import PurchaseOrder as XeroPurchaseOrder
# from xero_python.api_client import ApiClient
# from xero_python.api_client.configuration import Configuration
# from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.exceptions import AccountingBadRequestException # Keep if handled in views
from xero_python.identity import IdentityApi

from django.conf import settings
from workflow.templatetags.xero_tags import XERO_ENTITIES
from workflow.api.xero.sync import synchronise_xero_data, delete_clients_from_xero, get_last_modified_time
from workflow.api.xero.xero import (
    api_client, # Keep if needed elsewhere
    exchange_code_for_token,
    get_authentication_url,
    get_tenant_id, # Keep if needed elsewhere
    get_tenant_id_from_connections,
    get_token,
    get_valid_token,
    refresh_token,
)
from workflow.enums import InvoiceStatus, JobPricingType, QuoteStatus # Keep if needed
from workflow.models import Invoice, XeroToken, Client, Bill, CreditNote, XeroAccount, XeroJournal, CompanyDefaults, PurchaseOrder, Quote
from job.models import Job, JobFile, JobEvent, JobPricing
from workflow.utils import extract_messages
from workflow.services.xero_sync_service import XeroSyncService

# Import the new creator classes
from .xero_po_manager import XeroPurchaseOrderManager
from .xero_quote_manager import XeroQuoteManager
from .xero_invoice_manager import XeroInvoiceManager
# Import helpers if needed by remaining view functions
# from .helpers import format_date, clean_payload, convert_to_pascal_case

logger = logging.getLogger("xero")


# --- Authentication and Sync Views (Unchanged) ---

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
    
    # Log available tenant IDs after successful authentication
    try:
        identity_api = IdentityApi(api_client)
        connections = identity_api.get_connections()
        if connections:
            logger.info("Available Xero Organizations after authentication:")
            for conn in connections:
                logger.info(f"Tenant ID: {conn.tenant_id}, Name: {conn.tenant_name}")
        else:
            logger.info("No Xero organizations found after authentication")
    except Exception as e:
        logger.warning(f"Failed to log available tenant IDs after authentication: {str(e)}")
    
    redirect_url = request.session.pop("post_login_redirect", "/")
    return redirect(redirect_url)

# Refresh OAuth token and handle redirects
def refresh_xero_token(request: HttpRequest) -> HttpResponse:
    refreshed_token = refresh_token()
    if not refreshed_token:
        return redirect("api_xero_authenticate")
    return redirect("xero_index") # Redirect to index after refresh

# Xero connection success view
def success_xero_connection(request: HttpRequest) -> HttpResponse:
    return render(request, "xero/success_xero_connection.html")

def refresh_xero_data(request):
    """Refresh Xero data, handling authentication properly."""
    try:
        token = get_valid_token()
        if not token:
            logger.info("No valid token found, redirecting to Xero authentication")
            return redirect("api_xero_authenticate")
        return redirect("xero_sync_progress")
    except Exception as e:
        logger.error(f"Error while refreshing Xero data: {str(e)}")
        if "token" in str(e).lower():
            return redirect("api_xero_authenticate")
        return render(
            request, "general/generic_error.html", {"error_message": str(e)}
        )


# workflow/views/xero_sync_events.py

import json
import logging
import time

from django.core.cache import cache
from django.http import StreamingHttpResponse, HttpRequest
from django.utils import timezone
from django.views.decorators.http import require_GET

from workflow.services.xero_sync_service import XeroSyncService
from workflow.api.xero.xero import get_valid_token

logger = logging.getLogger("xero.events")


def generate_xero_sync_events():
    """
    SSE generator yielding JSON-encoded sync progress messages.

    Steps:
    1) Authenticate: ensure a valid Xero OAuth token is available.
    2) Emit an initial 'Starting Xero sync' event.
    3) Poll the XeroSyncService cache for new messages, streaming each one.
    4) Once no lock and no new messages, emit a final 'Sync stream ended' event.
    5) Handle unexpected errors by logging and emitting a single error event,
       then a final end-of-stream event without re-raising exceptions.
    """
    try:
        # 1) Authentication check
        if not get_valid_token():
            payload = {
                'datetime': timezone.now().isoformat(),
                'entity': 'sync',
                'severity': 'error',
                'message': 'No valid Xero token. Please authenticate.',
                'progress': None
            }
            yield f"data: {json.dumps(payload)}\n\n"
            return

        # 2) Starting event
        start_payload = {
            'datetime': timezone.now().isoformat(),
            'entity': 'sync',
            'severity': 'info',
            'message': 'Starting Xero sync',
            'progress': 0.0
        }
        yield f"data: {json.dumps(start_payload)}\n\n"

        # 3) Begin streaming cached messages
        task_id = XeroSyncService.get_active_task_id()
        last_index = 0

        while True:
            messages = XeroSyncService.get_messages(task_id, last_index)

            # 4a) If sync lock released and no pending messages → end
            if not cache.get('xero_sync_lock', False) and not messages:
                end_payload = {
                    'datetime': timezone.now().isoformat(),
                    'entity': 'sync',
                    'severity': 'info',
                    'message': 'Sync stream ended',
                    'progress': 1.0
                }
                yield f"data: {json.dumps(end_payload)}\n\n"
                break

            # 4b) Stream each new message
            for msg in messages:
                yield f"data: {json.dumps(msg)}\n\n"
                last_index += 1

            # 4c) Sleep to reduce CPU load
            time.sleep(0.5)

    except Exception:
        # 5) Unexpected error
        logger.exception("Unexpected error in generate_xero_sync_events")
        error_payload = {
            'datetime': timezone.now().isoformat(),
            'entity': 'sync',
            'severity': 'error',
            'message': 'Internal server error during sync.',
            'progress': None
        }
        yield f"data: {json.dumps(error_payload)}\n\n"

        final_payload = {
            'datetime': timezone.now().isoformat(),
            'entity': 'sync',
            'severity': 'info',
            'message': 'Sync stream ended',
            'progress': None
        }
        yield f"data: {json.dumps(final_payload)}\n\n"


@require_GET
def stream_xero_sync(request: HttpRequest) -> StreamingHttpResponse:
    """
    HTTP endpoint to serve an EventSource stream of Xero sync events.
    """
    response = StreamingHttpResponse(
        generate_xero_sync_events(),
        content_type='text/event-stream'
    )
    # Prevent Django or proxies from buffering
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

def ensure_xero_authentication():
    """
    Ensure the user is authenticated with Xero and retrieves the tenant ID.
    If authentication is missing, it returns a JSON response prompting login.
    """
    token = get_valid_token()
    if not token:
        return JsonResponse({"success": False, "redirect_to_auth": True, "message": "Your Xero session has expired. Please log in again."}, status=401)
    tenant_id = cache.get("xero_tenant_id") # Use consistent cache key
    if not tenant_id:
        try:
            tenant_id = get_tenant_id_from_connections()
            cache.set("xero_tenant_id", tenant_id, timeout=1800)
        except Exception as e:
            logger.error(f"Error retrieving tenant ID: {e}")
            return JsonResponse({"success": False, "redirect_to_auth": True, "message": "Unable to fetch Xero tenant ID. Please log in Xero again."}, status=401)
    return tenant_id

def _handle_creator_response(request: HttpRequest, response_data: JsonResponse, success_msg: str, failure_msg_prefix: str) -> JsonResponse:
    """Helper to process JsonResponse from creator methods."""
    if isinstance(response_data, JsonResponse):
        try:
            content = json.loads(response_data.content.decode())
            is_success = content.get("success", False) and response_data.status_code < 400
            if is_success:
                messages.success(request, success_msg)
            else:
                error_detail = content.get('message')
                if not error_detail or not isinstance(error_detail, str):
                    error_detail = content.get('error', 'An unknown error occurred.')

                if not isinstance(error_detail, str):
                    error_detail = "An unspecified error occurred."
                
                messages.error(request, f"{failure_msg_prefix}: {error_detail}")
        except (json.JSONDecodeError, AttributeError):
            # Handle non-JSON or unexpected content
            if response_data.status_code < 400: # Should ideally not happen if 'success' was false
                messages.success(request, f"{success_msg} (unexpected response format but status indicates success)")
            else:
                messages.error(request, f"{failure_msg_prefix}: An error occurred, but the details could not be read from the response.")
        return response_data
    else:
        # Should not happen if managers always return JsonResponse or raise Exception
        logger.error("Manager did not return JsonResponse or raise Exception.")
        messages.error(request, "An unexpected internal error occurred.")
        return JsonResponse({"success": False, "error": "Internal processing error."}, status=500)

def create_xero_invoice(request, job_id):
    """Creates an Invoice in Xero for a given job."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse): return tenant_id
    try:
        job = Job.objects.get(id=job_id)
        manager = XeroInvoiceManager(client=job.client, job=job)
        response_data = manager.create_document()
        return _handle_creator_response(request, response_data, "Invoice created successfully", "Failed to create invoice")
    except Job.DoesNotExist:
         messages.error(request, f"Job with ID {job_id} not found.")
         return JsonResponse({"success": False, "error": "Job not found.", "messages": extract_messages(request)}, status=404)
    except Exception as e:
        logger.error(f"Error in create_xero_invoice view: {str(e)}", exc_info=True)
        messages.error(request, "An unexpected error occurred while creating the invoice.")
        return JsonResponse({"success": False, "error": str(e), "messages": extract_messages(request)}, status=500)

def create_xero_purchase_order(request, purchase_order_id):
    """Creates a Purchase Order in Xero for a given purchase order."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse): return tenant_id
    try:
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        manager = XeroPurchaseOrderManager(purchase_order=purchase_order)
        # logger.info(f"Manager object type: {type(manager)}") # Keep for debugging if needed
        response_data = manager.create_document()
        return _handle_creator_response(request, response_data, "Purchase order submitted to Xero successfully", "Failed to create purchase order")
    except PurchaseOrder.DoesNotExist:
         messages.error(request, f"Purchase Order with ID {purchase_order_id} not found.")
         return JsonResponse({"success": False, "error": "Purchase Order not found.", "messages": extract_messages(request)}, status=404)
    except Exception as e:
        logger.error(f"Caught exception of type: {type(e)}")
        logger.error(f"Exception repr: {repr(e)}")
        if hasattr(e, 'body'): logger.error(f"Exception body: {getattr(e, 'body', 'N/A')}")
        if hasattr(e, 'response'): logger.error(f"Exception response: {getattr(e, 'response', 'N/A')}")
        logger.exception("Error occurred during create_xero_purchase_order view")
        user_error_message = "An error occurred while creating the purchase order in Xero. Please check logs."
        messages.error(request, user_error_message)
        return JsonResponse({"success": False, "error": user_error_message, "messages": extract_messages(request)}, status=500)

def create_xero_quote(request: HttpRequest, job_id) -> HttpResponse:
    """Creates a quote in Xero for a given job."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse): return tenant_id
    try:
        job = Job.objects.get(id=job_id)
        manager = XeroQuoteManager(client=job.client, job=job)
        response_data = manager.create_document()
        return _handle_creator_response(request, response_data, "Quote created successfully", "Failed to create quote")
    except Job.DoesNotExist:
         messages.error(request, f"Job with ID {job_id} not found.")
         return JsonResponse({"success": False, "error": "Job not found.", "messages": extract_messages(request)}, status=404)
    except Exception as e:
        logger.error(f"Error in create_xero_quote view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while creating the quote: {str(e)}")
        return JsonResponse({"success": False, "error": str(e), "messages": extract_messages(request)}, status=500)

def delete_xero_invoice(request: HttpRequest, job_id) -> HttpResponse:
    """Deletes an invoice in Xero for a given job."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse): return tenant_id
    try:
        job = Job.objects.get(id=job_id)
        manager = XeroInvoiceManager(client=job.client, job=job)
        response_data = manager.delete_document()
        return _handle_creator_response(request, response_data, "Invoice deleted successfully", "Failed to delete invoice")
    except Job.DoesNotExist:
         messages.error(request, f"Job with ID {job_id} not found.")
         return JsonResponse({"success": False, "error": "Job not found.", "messages": extract_messages(request)}, status=404)
    except Exception as e:
        logger.error(f"Error in delete_xero_invoice view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while deleting the invoice: {str(e)}")
        return JsonResponse({"success": False, "error": str(e), "messages": extract_messages(request)}, status=500)

def delete_xero_quote(request: HttpRequest, job_id: uuid) -> HttpResponse:
    """Deletes a quote in Xero for a given job."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse): return tenant_id
    try:
        job = Job.objects.get(id=job_id)
        manager = XeroQuoteManager(client=job.client, job=job)
        response_data = manager.delete_document()
        return _handle_creator_response(request, response_data, "Quote deleted successfully", "Failed to delete quote")
    except Job.DoesNotExist:
         messages.error(request, f"Job with ID {job_id} not found.")
         return JsonResponse({"success": False, "error": "Job not found.", "messages": extract_messages(request)}, status=404)
    except Exception as e:
        logger.error(f"Error in delete_xero_quote view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while deleting the quote: {str(e)}")
        return JsonResponse({"success": False, "error": str(e), "messages": extract_messages(request)}, status=500)


def delete_xero_purchase_order(request: HttpRequest, purchase_order_id: uuid.UUID) -> HttpResponse: 
    """Deletes a Purchase Order in Xero."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse): return tenant_id
    try:
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        # Assuming XeroPurchaseOrderManager has a delete_document method similar to others
        manager = XeroPurchaseOrderManager(purchase_order=purchase_order)
        response_data = manager.delete_document()
        return _handle_creator_response(request, response_data, "Purchase Order deleted successfully from Xero", "Failed to delete Purchase Order from Xero")
    except PurchaseOrder.DoesNotExist:
        messages.error(request, f"Purchase Order with ID {purchase_order_id} not found.")
        return JsonResponse({"success": False, "error": "Purchase Order not found.", "messages": extract_messages(request)}, status=404)
    except Exception as e:
        logger.error(f"Error in delete_xero_purchase_order view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while deleting the Purchase Order from Xero: {str(e)}")
        return JsonResponse({"success": False, "error": str(e), "messages": extract_messages(request)}, status=500)


def xero_disconnect(request):
    """Disconnects from Xero by clearing the token from cache and database."""
    try: # Corrected indentation
        cache.delete('xero_token')
        cache.delete('xero_tenant_id') # Use consistent cache key
        XeroToken.objects.all().delete()
        messages.success(request, "Successfully disconnected from Xero")
    except Exception as e: # Corrected indentation
        logger.error(f"Error disconnecting from Xero: {str(e)}")
        messages.error(request, "Failed to disconnect from Xero")
    return redirect("/") # Corrected indentation


class XeroIndexView(TemplateView):
    """Note this page is currently inaccessible. We are using a dropdown menu instead."""
    template_name = "xero_index.html"

def xero_sync_progress_page(request):
    """Render the Xero sync progress page."""
    try:
        token = get_valid_token()
        if not token:
            logger.info("No valid token found, redirecting to Xero authentication")
            return redirect("api_xero_authenticate")
        # Ensure this import works correctly after refactor
        from workflow.templatetags.xero_tags import XERO_ENTITIES
        return render(request, "xero/xero_sync_progress.html", {'XERO_ENTITIES': XERO_ENTITIES})
    except Exception as e:
        logger.error(f"Error accessing sync progress page: {str(e)}")
        if "token" in str(e).lower():
            return redirect("api_xero_authenticate")
        return render(request, "general/generic_error.html", {"error_message": str(e)})

def get_xero_sync_info(request):
    """Get current sync status and last sync times."""
    try:
        token = get_valid_token()
        if not token:
            return JsonResponse({'error': 'No valid Xero token. Please authenticate.', 'redirect_to_auth': True}, status=401)
        last_syncs = {
            'accounts': XeroAccount.objects.order_by('-xero_last_synced').first().xero_last_synced if XeroAccount.objects.exists() else None,
            'contacts': Client.objects.order_by('-xero_last_synced').first().xero_last_synced if Client.objects.exists() else None,
            'invoices': Invoice.objects.order_by('-xero_last_synced').first().xero_last_synced if Invoice.objects.exists() else None,
            'bills': Bill.objects.order_by('-xero_last_synced').first().xero_last_synced if Bill.objects.exists() else None,
            'quotes': Quote.objects.order_by('-xero_last_synced').first().xero_last_synced if Quote.objects.exists() else None,
            'purchase_orders': PurchaseOrder.objects.order_by('-xero_last_synced').first().xero_last_synced if PurchaseOrder.objects.exists() else None,
            'credit_notes': CreditNote.objects.order_by('-xero_last_synced').first().xero_last_synced if CreditNote.objects.exists() else None,
            'journals': XeroJournal.objects.order_by('-xero_last_synced').first().xero_last_synced if XeroJournal.objects.exists() else None,
        }
        sync_range = "Syncing data since last successful sync"
        sync_in_progress = cache.get('xero_sync_lock', False)
        return JsonResponse({'last_syncs': last_syncs, 'sync_range': sync_range, 'sync_in_progress': sync_in_progress})
    except Exception as e:
        logger.error(f"Error getting sync info: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def start_xero_sync(request):
    """
    View function to start a Xero sync as a background task.
    """
    try:
        token = get_valid_token()
        if not token:
            return JsonResponse({'error': 'No valid token. Please authenticate.'}, status=401)
        
        # Start sync using the service
        task_id, is_new = XeroSyncService.start_sync()
        
        if not task_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to start sync. The scheduler may not be running or a sync is already in progress.'
            }, status=500)
        
        message = 'Started new Xero sync' if is_new else 'A sync is already running'
        return JsonResponse({
            'status': 'success',
            'message': message,
            'task_id': task_id
        })
    except Exception as e:
        logger.error(f"Error starting Xero sync: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    
@require_POST
def trigger_xero_sync(request):
    """
    Manual “Sync now” endpoint. Returns the task_id so the frontend
    can connect to the same SSE stream.
    """
    # Ensure user is authenticated with Xero
    tenant = ensure_xero_authentication()
    if isinstance(tenant, JsonResponse):
        return tenant

    task_id, started = XeroSyncService.start_sync()
    if not task_id:
        return JsonResponse({'success': False, 'message': 'Unable to start sync.'}, status=400)

    return JsonResponse({
        'success': True,
        'task_id': task_id,
        'started': started
    })
