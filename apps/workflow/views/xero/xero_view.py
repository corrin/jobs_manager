# workflow/views/xero_view.py
import json
import logging
import time
import uuid

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from xero_python.identity import IdentityApi

from apps.accounting.models import Bill, CreditNote, Invoice, Quote
from apps.client.models import Client
from apps.job.models import Job
from apps.purchasing.models import PurchaseOrder, Stock
from apps.workflow.api.pagination import FiftyPerPagePagination
from apps.workflow.api.xero.xero import (
    api_client,
    exchange_code_for_token,
    get_authentication_url,
    get_tenant_id_from_connections,
    get_valid_token,
    refresh_token,
)
from apps.workflow.models import XeroAccount, XeroError, XeroJournal, XeroToken
from apps.workflow.serializers import (
    XeroAuthenticationErrorResponseSerializer,
    XeroDocumentErrorResponseSerializer,
    XeroDocumentSuccessResponseSerializer,
    XeroErrorSerializer,
    XeroPingResponseSerializer,
    XeroSseEventSerializer,
    XeroSyncInfoResponseSerializer,
    XeroSyncStartResponseSerializer,
    XeroTriggerSyncResponseSerializer,
)
from apps.workflow.services.error_persistence import persist_app_error
from apps.workflow.services.xero_sync_service import XeroSyncService

from .xero_invoice_manager import XeroInvoiceManager

# Import the new creator classes
from .xero_po_manager import XeroPurchaseOrderManager
from .xero_quote_manager import XeroQuoteManager

logger = logging.getLogger("xero")


# Xero Authentication (Step 1: Redirect user to Xero OAuth2 login)
@csrf_exempt
def xero_authenticate(request: HttpRequest) -> HttpResponse:
    state = str(uuid.uuid4())
    request.session["oauth_state"] = state
    redirect_after_login = request.GET.get("next", "/")
    request.session["post_login_redirect"] = redirect_after_login
    authorization_url = get_authentication_url(state)
    return redirect(authorization_url)


# OAuth callback
@csrf_exempt
def xero_oauth_callback(request: HttpRequest) -> HttpResponse:
    code = request.GET.get("code")
    state = request.GET.get("state")
    session_state = request.session.get("oauth_state")
    result = exchange_code_for_token(code, state, session_state)
    if "error" in result:
        return render(
            request, "xero/error_xero_auth.html", {"error_message": result["error"]}
        )

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
        logger.warning(
            f"Failed to log available tenant IDs after authentication: {str(e)}"
        )

    redirect_path = request.session.pop("post_login_redirect", "/")
    if not redirect_path:
        redirect_path = "/"

    frontend_url = getattr(settings, "FRONT_END_URL", None)

    if not isinstance(frontend_url, str) or not frontend_url:
        logger.info(f"Redirecting user to frontend: {redirect_path}")
        return redirect(redirect_path)

    if not redirect_path.startswith("/"):
        logger.info(f"Redirecting user to frontend: {frontend_url.rstrip('/')}/")
        return redirect(frontend_url.rstrip("/") + "/")

    redirect_url = frontend_url.rstrip("/") + redirect_path
    logger.info(f"Redirecting user to frontend: {redirect_url}")
    return redirect(redirect_url)


# Refresh OAuth token and handle redirects
@csrf_exempt
def refresh_xero_token(request: HttpRequest) -> HttpResponse:
    refreshed_token = refresh_token()
    if not refreshed_token:
        return redirect("api_xero_authenticate")
    return redirect("xero_index")  # Redirect to index after refresh


# Xero connection success view
@csrf_exempt
def success_xero_connection(request: HttpRequest) -> HttpResponse:
    return render(request, "xero/success_xero_connection.html")


@csrf_exempt
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
        return render(request, "general/generic_error.html", {"error_message": str(e)})


# workflow/views/xero_sync_events.py


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
                "datetime": timezone.now().isoformat(),
                "entity": "sync",
                "severity": "error",
                "message": "No valid Xero token. Please authenticate.",
                "progress": None,
            }
            yield f"data: {json.dumps(payload)}\n\n"
            return

        # 2) Starting event
        start_payload = {
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "info",
            "message": "Starting Xero sync",
            "progress": 0.0,
        }
        yield f"data: {json.dumps(start_payload)}\n\n"

        # 3) Begin streaming cached messages
        task_id = XeroSyncService.get_active_task_id()
        last_index = 0

        while True:
            messages = XeroSyncService.get_messages(task_id, last_index)

            # 4a) If sync lock released and no pending messages → end
            if not cache.get("xero_sync_lock", False) and not messages:
                # Check if there's an error in the sync messages
                error_found = False
                error_messages = []
                all_msgs = XeroSyncService.get_messages(task_id, 0)
                for m in all_msgs:
                    if m.get("severity") == "error":
                        error_found = True
                        error_messages.append(m.get("message"))
                end_payload = {
                    "datetime": timezone.now().isoformat(),
                    "entity": "sync",
                    "severity": "info",
                    "message": "Sync stream ended",
                    "progress": 1.0,
                    "sync_status": "error" if error_found else "success",
                }
                if error_found:
                    end_payload["error_messages"] = error_messages
                logger.info(f"[SSE END PAYLOAD] {json.dumps(end_payload)}")
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
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "error",
            "message": "Internal server error during sync.",
            "progress": None,
        }
        yield f"data: {json.dumps(error_payload)}\n\n"

        final_payload = {
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "info",
            "message": "Sync stream ended",
            "progress": None,
        }
        yield f"data: {json.dumps(final_payload)}\n\n"


@csrf_exempt
@extend_schema(
    description="Xero Sync Event Stream",
    responses={200: XeroSseEventSerializer(many=True)},
)
@require_GET
def stream_xero_sync(request: HttpRequest) -> StreamingHttpResponse:
    """
    HTTP endpoint to serve an EventSource stream of Xero sync events.
    """
    response = StreamingHttpResponse(
        generate_xero_sync_events(), content_type="text/event-stream"
    )
    # Prevent Django or proxies from buffering
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def ensure_xero_authentication():
    """
    Ensure the user is authenticated with Xero and retrieves the tenant ID.
    If authentication is missing, it returns a JSON response prompting login.
    """
    token = get_valid_token()
    if not token:
        error_response = {
            "success": False,
            "redirect_to_auth": True,
            "message": "Your Xero session has expired. Please log in again.",
        }
        error_serializer = XeroAuthenticationErrorResponseSerializer(error_response)
        return JsonResponse(error_serializer.data, status=401)

    tenant_id = cache.get("xero_tenant_id")  # Use consistent cache key
    if not tenant_id:
        try:
            tenant_id = get_tenant_id_from_connections()
            cache.set("xero_tenant_id", tenant_id, timeout=1800)
        except Exception as e:
            logger.error(f"Error retrieving tenant ID: {e}")
            error_response = {
                "success": False,
                "redirect_to_auth": True,
                "message": "Unable to fetch Xero tenant ID. Please log in Xero again.",
            }
            error_serializer = XeroAuthenticationErrorResponseSerializer(error_response)
            return JsonResponse(error_serializer.data, status=401)
    return tenant_id


@csrf_exempt
@extend_schema(
    tags=["Xero"],
    request=None,
    responses={
        201: XeroDocumentSuccessResponseSerializer,
        400: XeroDocumentErrorResponseSerializer,
        404: XeroDocumentErrorResponseSerializer,
        500: XeroDocumentErrorResponseSerializer,
    },
    description="Creates an invoice in Xero for the specified job",
)
@api_view(["POST"])
def create_xero_invoice(request: Request, job_id: uuid.UUID) -> Response:
    """Creates an Invoice in Xero for a given job."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse):
        # Convert JsonResponse to DRF Response
        return Response(json.loads(tenant_id.content), status=tenant_id.status_code)

    try:
        job = Job.objects.get(id=job_id)
        manager = XeroInvoiceManager(client=job.client, job=job)
        result_data = manager.create_document()

        if result_data.get("success"):
            messages.success(request, "Invoice created successfully")
            serializer = XeroDocumentSuccessResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            messages.error(
                request, f"Failed to create invoice: {result_data.get('error')}"
            )
            serializer = XeroDocumentErrorResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    except Job.DoesNotExist:
        error_data = {"success": False, "error": f"Job with ID {job_id} not found."}
        messages.error(request, error_data["error"])
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        persist_app_error(e, job_id=str(job_id))
        error_data = {"success": False, "error": "An unexpected server error occurred."}
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@extend_schema(
    tags=["Xero"],
    request=None,
    responses={
        201: XeroDocumentSuccessResponseSerializer,
        400: XeroDocumentErrorResponseSerializer,
        404: XeroDocumentErrorResponseSerializer,
        500: XeroDocumentErrorResponseSerializer,
    },
    description="Creates or updates a Purchase Order in Xero.",
    parameters=[
        OpenApiParameter(
            name="purchase_order_id",
            location=OpenApiParameter.PATH,
            type={"type": "string", "format": "uuid"},
            required=True,
        )
    ],
)
@api_view(["POST"])
def create_xero_purchase_order(
    request: Request, purchase_order_id: uuid.UUID
) -> Response:
    """Creates or updates a Purchase Order in Xero for a given purchase order."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse):
        return Response(json.loads(tenant_id.content), status=tenant_id.status_code)

    try:
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        logger.info(
            f"Starting Xero sync for PO {purchase_order_id}",
            extra={
                "purchase_order_id": str(purchase_order_id),
                "po_number": purchase_order.po_number,
                "supplier_id": str(purchase_order.supplier.id)
                if purchase_order.supplier
                else None,
                "user_id": str(request.user.id)
                if request.user.is_authenticated
                else None,
            },
        )
        manager = XeroPurchaseOrderManager(purchase_order=purchase_order)
        result_data = manager.sync_to_xero()

        logger.info(
            f"Manager returned result for PO {purchase_order_id}: success={result_data.get('success')}",
            extra={
                "purchase_order_id": str(purchase_order_id),
                "result_data": result_data,
            },
        )

        # Handle unhappy case first
        if not result_data.get("success"):
            error_msg = result_data.get("error", "Unknown error")
            error_type = result_data.get("error_type", "unknown")
            status_code = result_data.get("status", 400)

            # Persist error for unhappy cases
            persist_app_error(
                ValueError(error_msg),
                additional_context={
                    "purchase_order_id": str(purchase_order_id),
                    "error_type": error_type,
                    "result_data": result_data,
                    "user_id": str(request.user.id)
                    if request.user.is_authenticated
                    else None,
                    "request_path": request.path,
                    "request_method": request.method,
                },
            )

            messages.error(request, f"Failed to sync Purchase Order: {error_msg}")
            logger.warning(
                f"Failed to sync PO {purchase_order_id}: {error_msg}",
                extra={
                    "purchase_order_id": str(purchase_order_id),
                    "error_message": error_msg,
                    "error_type": error_type,
                    "result_data": result_data,
                },
            )
            serializer = XeroDocumentErrorResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status_code)

        # Handle happy case
        messages.success(request, "Purchase Order synced successfully with Xero.")
        logger.info(
            f"Successfully synced PO {purchase_order_id} to Xero",
            extra={
                "purchase_order_id": str(purchase_order_id),
                "xero_id": result_data.get("xero_id"),
                "online_url": result_data.get("online_url"),
            },
        )
        serializer = XeroDocumentSuccessResponseSerializer(data=result_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except PurchaseOrder.DoesNotExist:
        logger.warning(
            f"Purchase Order not found: {purchase_order_id}",
            extra={
                "purchase_order_id": str(purchase_order_id),
                "user_id": str(request.user.id)
                if request.user.is_authenticated
                else None,
            },
        )
        error_data = {
            "success": False,
            "error": f"Purchase Order with ID {purchase_order_id} not found.",
        }
        messages.error(request, error_data["error"])
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Unexpected error in create_xero_purchase_order view for PO {purchase_order_id}",
            extra={
                "purchase_order_id": str(purchase_order_id),
                "user_id": str(request.user.id)
                if request.user.is_authenticated
                else None,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        persist_app_error(
            e,
            additional_context={
                "purchase_order_id": str(purchase_order_id),
                "user_id": str(request.user.id)
                if request.user.is_authenticated
                else None,
                "request_path": request.path,
                "request_method": request.method,
            },
        )
        error_data = {"success": False, "error": "An unexpected server error occurred."}
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@extend_schema(
    tags=["Xero"],
    request=None,
    responses={
        201: XeroDocumentSuccessResponseSerializer,
        404: XeroDocumentErrorResponseSerializer,
        500: XeroDocumentErrorResponseSerializer,
    },
    description="Creates a quote in Xero for the specified job",
)
@api_view(["POST"])
def create_xero_quote(request: Request, job_id: uuid.UUID) -> Response:
    """Creates a quote in Xero for a given job."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse):
        return Response(json.loads(tenant_id.content), status=tenant_id.status_code)

    try:
        job = Job.objects.get(id=job_id)
        manager = XeroQuoteManager(client=job.client, job=job)
        result_data = manager.create_document()

        if result_data.get("success"):
            messages.success(request, "Quote created successfully.")
            serializer = XeroDocumentSuccessResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            messages.error(
                request, f"Failed to create quote: {result_data.get('error')}"
            )
            serializer = XeroDocumentErrorResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    except Job.DoesNotExist:
        error_data = {"success": False, "error": f"Job with ID {job_id} not found."}
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        persist_app_error(e, job_id=str(job_id))
        error_data = {"success": False, "error": "An unexpected server error occurred."}
        return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@extend_schema(
    tags=["Xero"],
    request=None,
    responses={
        200: XeroDocumentSuccessResponseSerializer,
        400: XeroDocumentErrorResponseSerializer,
        404: XeroDocumentErrorResponseSerializer,
        500: XeroDocumentErrorResponseSerializer,
    },
    description="Deletes a specific invoice in Xero for a given job, identified by its Xero ID.",
    parameters=[
        OpenApiParameter(
            name="job_id", location=OpenApiParameter.PATH, required=True, type=str
        ),
        OpenApiParameter(
            name="xero_invoice_id",
            location=OpenApiParameter.QUERY,
            required=True,
            type=str,
        ),
    ],
)
@api_view(["DELETE"])
def delete_xero_invoice(request: Request, job_id: uuid.UUID) -> Response:
    """Deletes a specific invoice in Xero for a given job, identified by its Xero ID."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse):
        return Response(json.loads(tenant_id.content), status=tenant_id.status_code)

    xero_invoice_id = request.query_params.get("xero_invoice_id")
    if not xero_invoice_id:
        error_data = {
            "success": False,
            "error": "xero_invoice_id is a required query parameter.",
        }
        return Response(error_data, status=status.HTTP_400_BAD_REQUEST)

    try:
        job = Job.objects.get(id=job_id)
        invoice = Invoice.objects.get(xero_id=xero_invoice_id, job=job)
        manager = XeroInvoiceManager(
            client=job.client, job=job, xero_invoice_id=invoice.xero_id
        )
        result_data: dict = manager.delete_document()

        if result_data.get("success"):
            messages.success(request, "Invoice deleted successfully.")
            serializer = XeroDocumentSuccessResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            messages.error(
                request, f"Failed to delete invoice: {result_data.get('error')}"
            )
            serializer = XeroDocumentErrorResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    except Job.DoesNotExist:
        error_data = {"success": False, "error": f"Job with ID {job_id} not found."}
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)
    except Invoice.DoesNotExist:
        error_data = {
            "success": False,
            "error": f"Invoice with Xero ID {xero_invoice_id} not found for this job.",
        }
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        persist_app_error(e, job_id=str(job_id))
        error_data = {"success": False, "error": "An unexpected server error occurred."}
        return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@extend_schema(
    tags=["Xero"],
    request=None,
    responses={
        200: XeroDocumentSuccessResponseSerializer,
        404: XeroDocumentErrorResponseSerializer,
        500: XeroDocumentErrorResponseSerializer,
    },
    description="Deletes a quote in Xero for the specified job",
)
@api_view(["DELETE"])
def delete_xero_quote(request: Request, job_id: uuid.UUID) -> Response:
    """Deletes a quote in Xero for a given job."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse):
        return Response(json.loads(tenant_id.content), status=tenant_id.status_code)

    try:
        job = Job.objects.get(id=job_id)
        manager = XeroQuoteManager(client=job.client, job=job)
        result_data: dict = manager.delete_document()

        if result_data.get("success"):
            messages.success(request, "Quote deleted successfully.")
            serializer = XeroDocumentSuccessResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            messages.error(
                request, f"Failed to delete quote: {result_data.get('error')}"
            )
            serializer = XeroDocumentErrorResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    except Job.DoesNotExist:
        error_data = {"success": False, "error": f"Job with ID {job_id} not found."}
        messages.error(request, error_data["error"])
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(f"Error in delete_xero_quote view for job {job_id}")
        persist_app_error(e, job_id=str(job_id))
        error_data = {"success": False, "error": "An unexpected server error occurred."}
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@extend_schema(
    tags=["Xero"],
    request=None,
    responses={
        200: XeroDocumentSuccessResponseSerializer,
        404: XeroDocumentErrorResponseSerializer,
        500: XeroDocumentErrorResponseSerializer,
    },
    description="Deletes a purchase order in Xero for the specified purchase order",
)
@api_view(["DELETE"])
def delete_xero_purchase_order(
    request: Request, purchase_order_id: uuid.UUID
) -> Response:
    """Deletes a Purchase Order in Xero."""
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse):
        return Response(json.loads(tenant_id.content), status=tenant_id.status_code)

    try:
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        manager = XeroPurchaseOrderManager(purchase_order=purchase_order)
        result_data = manager.delete_document()

        if result_data.get("success"):
            messages.success(request, "Purchase Order deleted successfully.")
            serializer = XeroDocumentSuccessResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            messages.error(
                request, f"Failed to delete Purchase Order: {result_data.get('error')}"
            )
            serializer = XeroDocumentErrorResponseSerializer(data=result_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    except PurchaseOrder.DoesNotExist:
        error_data = {
            "success": False,
            "error": f"Purchase Order with ID {purchase_order_id} not found.",
        }
        messages.error(request, error_data["error"])
        return Response(error_data, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(
            f"Error in delete_xero_purchase_order view for PO {purchase_order_id}"
        )
        persist_app_error(e)
        error_data = {"success": False, "error": "An unexpected server error occurred."}
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def xero_disconnect(request):
    """Disconnects from Xero by clearing the token from cache and database."""
    try:  # Corrected indentation
        cache.delete("xero_token")
        cache.delete("xero_tenant_id")  # Use consistent cache key
        XeroToken.objects.all().delete()
        messages.success(request, "Successfully disconnected from Xero")
    except Exception as e:  # Corrected indentation
        logger.error(f"Error disconnecting from Xero: {str(e)}")
        messages.error(request, "Failed to disconnect from Xero")
    return redirect("/")  # Corrected indentation


class XeroIndexView(TemplateView):
    """Note this page is currently inaccessible. We are using a dropdown menu instead."""

    template_name = "xero_index.html"


@csrf_exempt
def xero_sync_progress_page(request):
    """Render the Xero sync progress page."""
    try:
        token = get_valid_token()
        if not token:
            logger.info("No valid token found, redirecting to Xero authentication")
            return redirect("api_xero_authenticate")
        # Ensure this import works correctly after refactor
        from apps.workflow.templatetags.xero_tags import XERO_ENTITIES

        return render(
            request, "xero/xero_sync_progress.html", {"XERO_ENTITIES": XERO_ENTITIES}
        )
    except Exception as e:
        logger.error(f"Error accessing sync progress page: {str(e)}")
        if "token" in str(e).lower():
            return redirect("api_xero_authenticate")
        return render(request, "general/generic_error.html", {"error_message": str(e)})


@csrf_exempt
def get_xero_sync_info(request):
    """Get current sync status and last sync times, including Xero Items/Stock."""
    try:
        token = get_valid_token()
        if not token:
            return JsonResponse(
                {
                    "error": "No valid Xero token. Please authenticate.",
                    "redirect_to_auth": True,
                },
                status=401,
            )
        last_syncs = {
            "accounts": (
                XeroAccount.objects.order_by("-xero_last_synced")
                .first()
                .xero_last_synced
                if XeroAccount.objects.exists()
                else None
            ),
            "contacts": (
                Client.objects.order_by("-xero_last_synced").first().xero_last_synced
                if Client.objects.exists()
                else None
            ),
            "invoices": (
                Invoice.objects.order_by("-xero_last_synced").first().xero_last_synced
                if Invoice.objects.exists()
                else None
            ),
            "bills": (
                Bill.objects.order_by("-xero_last_synced").first().xero_last_synced
                if Bill.objects.exists()
                else None
            ),
            "quotes": (
                Quote.objects.order_by("-xero_last_synced").first().xero_last_synced
                if Quote.objects.exists()
                else None
            ),
            "purchase_orders": (
                PurchaseOrder.objects.order_by("-xero_last_synced")
                .first()
                .xero_last_synced
                if PurchaseOrder.objects.exists()
                else None
            ),
            "credit_notes": (
                CreditNote.objects.order_by("-xero_last_synced")
                .first()
                .xero_last_synced
                if CreditNote.objects.exists()
                else None
            ),
            "journals": (
                XeroJournal.objects.order_by("-xero_last_synced")
                .first()
                .xero_last_synced
                if XeroJournal.objects.exists()
                else None
            ),
            "stock": (
                Stock.objects.order_by("-xero_last_modified").first().xero_last_modified
                if Stock.objects.exists()
                else None
            ),
        }
        sync_range = "Syncing data since last successful sync"
        sync_in_progress = cache.get("xero_sync_lock", False)

        response_data = {
            "last_syncs": last_syncs,
            "sync_range": sync_range,
            "sync_in_progress": sync_in_progress,
        }

        response_serializer = XeroSyncInfoResponseSerializer(response_data)
        return JsonResponse(response_serializer.data)
    except Exception as e:
        logger.error(f"Error getting sync info: {str(e)}")
        error_response = {"error": str(e)}
        error_serializer = XeroSyncInfoResponseSerializer(error_response)
        return JsonResponse(error_serializer.data, status=500)


@csrf_exempt
def start_xero_sync(request):
    """
    View function to start a Xero sync as a background task.
    """
    try:
        token = get_valid_token()
        if not token:
            error_response = {"error": "No valid token. Please authenticate."}
            error_serializer = XeroSyncStartResponseSerializer(error_response)
            return JsonResponse(error_serializer.data, status=401)

        # Start sync using the service
        task_id, is_new = XeroSyncService.start_sync()

        if not task_id:
            error_response = {
                "status": "error",
                "message": "Failed to start sync. The scheduler may not be running or a sync is already in progress.",
            }
            error_serializer = XeroSyncStartResponseSerializer(error_response)
            return JsonResponse(error_serializer.data, status=500)

        message = "Started new Xero sync" if is_new else "A sync is already running"
        response_data = {"status": "success", "message": message, "task_id": task_id}

        response_serializer = XeroSyncStartResponseSerializer(response_data)
        return JsonResponse(response_serializer.data)
    except Exception as e:
        logger.error(f"Error starting Xero sync: {str(e)}")
        error_response = {"error": str(e)}
        error_serializer = XeroSyncStartResponseSerializer(error_response)
        return JsonResponse(error_serializer.data, status=500)


@csrf_exempt
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
        error_response = {"success": False, "message": "Unable to start sync."}
        error_serializer = XeroTriggerSyncResponseSerializer(error_response)
        return JsonResponse(error_serializer.data, status=400)

    response_data = {"success": True, "task_id": task_id, "started": started}
    response_serializer = XeroTriggerSyncResponseSerializer(response_data)
    return JsonResponse(response_serializer.data)


@csrf_exempt
def xero_ping(request: HttpRequest) -> JsonResponse:
    """
    Simple endpoint to check if the user is authenticated with Xero.
    Returns {"connected": true} or {"connected": false}.
    Always returns HTTP 200 for frontend simplicity.
    """
    try:
        token = get_valid_token()
        is_connected = bool(token)
        logger.info(f"Xero ping: connected={is_connected}")

        response_data = {"connected": is_connected}
        response_serializer = XeroPingResponseSerializer(response_data)
        return JsonResponse(response_serializer.data)
    except Exception as e:
        logger.error(f"Error in xero_ping: {str(e)}")
        error_response = {"connected": False}
        error_serializer = XeroPingResponseSerializer(error_response)
        return JsonResponse(error_serializer.data)


class XeroErrorListAPIView(ListAPIView):
    """
    API view for listing Xero synchronization errors.

    Returns a paginated list of all XeroError records ordered by timestamp
    (most recent first). Useful for monitoring and debugging Xero integration
    issues.

    Endpoint: /api/xero/errors/
    """

    queryset = XeroError.objects.all().order_by("-timestamp")
    serializer_class = XeroErrorSerializer
    pagination_class = FiftyPerPagePagination


class XeroErrorDetailAPIView(RetrieveAPIView):
    """
    API view for retrieving a single Xero synchronization error.

    Returns detailed information about a specific XeroError record
    including error message, context, and timestamp. Used for investigating
    specific Xero integration failures.

    Endpoint: /api/xero/errors/<id>/
    """

    queryset = XeroError.objects.all()
    serializer_class = XeroErrorSerializer
