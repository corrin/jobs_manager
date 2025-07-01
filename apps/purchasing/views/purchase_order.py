import base64
import json
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, TemplateView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Django and Python Standard Library imports first
from apps.job.models import Job

# Apps Models
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine

# Apps Services
from apps.purchasing.services.purchase_order_email_service import (
    create_purchase_order_email,
)
from apps.purchasing.services.purchase_order_pdf_service import (
    create_purchase_order_pdf,
)
from apps.purchasing.services.quote_to_po_service import (
    create_po_from_quote,
    save_quote_file,
)
from apps.workflow.models import AIProvider

# Apps Utils and Managers
from apps.workflow.utils import extract_messages
from apps.workflow.views.xero.xero_po_manager import XeroPurchaseOrderManager

# Apps Forms


logger = logging.getLogger(__name__)


class PurchaseOrderListView(LoginRequiredMixin, ListView):
    """View to list all purchase orders."""

    model = PurchaseOrder
    template_name = "purchasing/purchase_order_list.html"
    context_object_name = "purchase_orders"

    def get_queryset(self):
        """Return purchase orders ordered by PO number (descending)."""
        return PurchaseOrder.objects.all().order_by("-po_number")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Purchase Orders"
        return context


class PurchaseOrderCreateView(LoginRequiredMixin, TemplateView):
    """View to create or edit a purchase order, following the timesheet pattern."""

    template_name = "purchasing/purchase_order_form.html"

    def get(self, request, *args, **kwargs):
        # Check if we're editing an existing purchase order
        purchase_order_id = self.kwargs.get("pk")
        if not purchase_order_id:
            # Creating a new purchase order - reserve a PO number immediately
            purchase_order = PurchaseOrder(
                status="draft", order_date=timezone.now().date()
            )
            purchase_order.save()  # This will generate a unique PO number
            # Redirect to the URL with the new PO's ID
            return redirect("purchasing:purchase_orders_detail", pk=purchase_order.id)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Since we've redirected if no pk, we can assume pk exists
        purchase_order_id = self.kwargs.get("pk")
        purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
        context["title"] = f"Purchase Order {purchase_order.po_number}"
        context["purchase_order_id"] = str(purchase_order.id)  # Pass ID to template

        # Add supplier quote to context (it's a OneToOneField, not a collection)
        try:
            context["supplier_quote"] = purchase_order.supplier_quote
        except PurchaseOrder.supplier_quote.RelatedObjectDoesNotExist:
            context["supplier_quote"] = None

        # Fetch Xero details if available
        xero_online_url = purchase_order.online_url
        xero_id = purchase_order.xero_id
        purchase_order_status = purchase_order.status  # Fetch the status

        # Add purchase order data
        context["purchase_order_json"] = json.dumps(
            {
                "id": str(purchase_order.id),
                "po_number": purchase_order.po_number,
                "supplier": (
                    str(purchase_order.supplier.id) if purchase_order.supplier else None
                ),
                "supplier_name": (
                    purchase_order.supplier.name if purchase_order.supplier else None
                ),
                "client_xero_id": (
                    purchase_order.supplier.xero_contact_id
                    if purchase_order.supplier
                    and purchase_order.supplier.xero_contact_id
                    else None
                ),
                "order_date": (
                    purchase_order.order_date.isoformat()
                    if purchase_order.order_date
                    else None
                ),
                "expected_delivery": (
                    purchase_order.expected_delivery.isoformat()
                    if purchase_order.expected_delivery
                    else None
                ),
                "status": purchase_order_status,  # Use the fetched status
                "xero_id": (
                    str(xero_id) if xero_id else None
                ),  # Include Xero ID if exists
                "xero_online_url": xero_online_url,  # Include Xero URL if exists,
                "reference": (
                    purchase_order.reference if purchase_order.reference else None
                ),
            }
        )

        # Get line items for this purchase order
        assert isinstance(purchase_order, PurchaseOrder)  # Ensure type for Pylance
        line_items = (
            purchase_order.po_lines.all()
        )  # Use correct related_name 'po_lines'
        context["line_items_json"] = json.dumps(
            [
                {
                    "id": str(line.id),
                    "job": str(line.job.id) if line.job else None,
                    "job_display_name": line.job.job_display_name if line.job else None,
                    "description": line.description,
                    "quantity": float(line.quantity),
                    "unit_cost": (
                        float(line.unit_cost) if line.unit_cost is not None else None
                    ),
                    "price_tbc": line.price_tbc,
                    "total": float(line.quantity * (line.unit_cost or 0)),
                    "metal_type": line.metal_type or "unspecified",
                    "alloy": line.alloy or "",
                    "specifics": line.specifics or "",
                    "location": line.location or "",
                    "dimensions": line.dimensions or "",
                }
                for line in line_items
            ]
        )

        # Get active jobs for the line items - match exactly what timesheet view does
        jobs = Job.objects.filter(
            status__in=["quoting", "approved", "in_progress", "special"]
        ).select_related("client", "latest_estimate_pricing")

        context["jobs_json"] = json.dumps(
            [
                {
                    "id": str(job.id),
                    "job_number": job.job_number,
                    "name": job.name,
                    "client_name": job.client.name if job.client else "No Client",
                    "client_id": str(job.client.id) if job.client else None,
                    "job_display_name": job.job_display_name,
                    "estimated_materials": (
                        float(job.latest_estimate_pricing.total_material_cost)
                        if job.latest_estimate_pricing
                        else 0
                    ),  # Handle None case
                }
                for job in jobs
            ]
        )

        # Add Xero details to the main context for template access
        context["xero_purchase_order_url"] = xero_online_url
        context["xero_id"] = str(xero_id) if xero_id else None
        context["purchase_order_status"] = purchase_order_status
        return context

    def post(self, request, *args, **kwargs):
        """Handle form submission via AJAX."""
        try:
            purchase_order_data = json.loads(
                request.POST.get("purchase_order_data", "{}")
            )
            line_items_data = json.loads(request.POST.get("line_items_data", "[]"))

            # Get the client (supplier)
            client_id = purchase_order_data.get("supplier")

            # Create purchase order
            purchase_order = PurchaseOrder(
                supplier_id=client_id,
                order_date=purchase_order_data.get("order_date"),
                expected_delivery=purchase_order_data.get("expected_delivery"),
                status="draft",
            )
            purchase_order.save()

            # Create line items
            for item in line_items_data:
                PurchaseOrderLine.objects.create(
                    purchase_order=purchase_order,
                    job_id=item.get("job"),
                    description=item.get("description"),
                    quantity=item.get("quantity"),
                    unit_cost=item.get("unit_cost"),
                )

            messages.success(
                request,
                f"Purchase order {purchase_order.po_number} created successfully.",
            )
            return JsonResponse(
                {"success": True, "redirect_url": reverse_lazy("purchase_orders")}
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
@transaction.atomic
def autosave_purchase_order_view(request):
    request_timestamp = datetime.now().isoformat()

    try:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.error(f"Malformed JSON body: {str(e)}")
            return JsonResponse({"error": "Malformed JSON input"}, status=400)

        purchase_order_data = data.get("purchase_order", {})
        line_items = data.get("line_items", [])
        purchase_order_id = purchase_order_data.get("id")

        logger.info(
            f"[{request_timestamp}] autosave_purchase_order_view called. Incoming PO ID: {purchase_order_id}"
        )
        logger.debug("Request data: %s", json.dumps(data, indent=2))
        logger.debug(f"Number of line items: {len(line_items)}")

        if not purchase_order_id:
            logger.error("CRITICAL: Missing PO ID")
            return JsonResponse({"error": "Missing Purchase Order ID"}, status=400)

        saved_line_ids = [item.get("id") for item in line_items if item.get("id")]
        PurchaseOrderLine.objects.filter(purchase_order_id=purchase_order_id).exclude(
            id__in=saved_line_ids
        ).delete()

        try:
            purchase_order = PurchaseOrder.objects.select_for_update().get(
                id=purchase_order_id
            )
        except PurchaseOrder.DoesNotExist:
            logger.error(f"Purchase Order with ID {purchase_order_id} not found.")
            return JsonResponse(
                {
                    "error": "Purchase Order not found",
                    "messages": extract_messages(request),
                },
                status=404,
            )

        if "client_id" in purchase_order_data:
            purchase_order.supplier_id = purchase_order_data["client_id"]
        if "status" in purchase_order_data:
            purchase_order.status = purchase_order_data["status"]
        if "order_date" in purchase_order_data:
            purchase_order.order_date = purchase_order_data["order_date"]
        if "expected_delivery" in purchase_order_data:
            purchase_order.expected_delivery = (
                purchase_order_data["expected_delivery"] or None
            )
        if "reference" in purchase_order_data:
            purchase_order.reference = purchase_order_data["reference"]

        purchase_order.save()

        for item_data in line_items:
            line_id = item_data.get("id")
            PurchaseOrderLine.objects.update_or_create(
                id=line_id or None,
                purchase_order=purchase_order,
                defaults={
                    "job_id": item_data.get("job"),
                    "description": item_data.get("description"),
                    "quantity": item_data.get("quantity"),
                    "unit_cost": item_data.get("unit_cost"),
                    "price_tbc": item_data.get("price_tbc", False),
                    "metal_type": item_data.get("metal_type", "unspecified"),
                    "alloy": item_data.get("alloy", ""),
                    "specifics": item_data.get("specifics", ""),
                    "location": item_data.get("location", ""),
                    "dimensions": item_data.get("dimensions", ""),
                },
            )

        manager = XeroPurchaseOrderManager(purchase_order=purchase_order)

        if not manager.can_sync_to_xero():
            logger.warning(
                f"Cannot sync PO {purchase_order.id} to Xero - validation failed"
            )
            return JsonResponse(
                {
                    "success": True,
                    "is_incomplete_po": True,
                    "redirect_url": reverse(
                        "purchasing:purchase_orders_detail",
                        kwargs={"pk": purchase_order.id},
                    ),
                }
            )

        logger.info(f"Syncing purchase order {purchase_order.id} to Xero")
        raw_response = manager.sync_to_xero()
        response = json.loads(raw_response.content)

        if not response.get("success"):
            if response.get("is_incomplete_po"):
                logger.warning(
                    f"Cannot sync PO {purchase_order.id} to Xero - validation failed"
                )
                return JsonResponse({"success": True, "is_incomplete_po": True})

            logger.error(f"Sync failure: {response.get('error')}")
            messages.error(
                request, f"Failed to sync with Xero: {response.get('error')}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": response.get("error", "Failed to sync with Xero"),
                    "exception_type": response.get("exception_type"),
                    "redirect_url": reverse(
                        "purchasing:purchase_orders_detail",
                        kwargs={"pk": purchase_order.id},
                    ),
                }
            )

        logger.info(f"Successfully synced PO {purchase_order.id} to Xero")

        return JsonResponse(
            {
                "success": True,
                "xero_url": purchase_order.online_url,
                "xero_id": (
                    str(purchase_order.xero_id) if purchase_order.xero_id else None
                ),
                "redirect_url": reverse(
                    "purchasing:purchase_orders_detail",
                    kwargs={"pk": purchase_order.id},
                ),
            }
        )

    except Exception as e:
        logger.exception("Error during purchase order autosave")
        messages.error(request, f"An error occurred: {str(e)}")
        return JsonResponse(
            {
                "error": f"Unexpected server error: {str(e)}",
                "messages": extract_messages(request),
            },
            status=500,
        )


@require_http_methods(["POST"])
def delete_purchase_order_view(request, pk):
    if not pk:
        return JsonResponse(
            {"success": False, "error": "Missing PO id in the request."}, status=400
        )

    try:
        po: PurchaseOrder = PurchaseOrder.objects.get(id=pk)

        if po.status != "draft":
            raise Exception(
                "Invalid PO status - cannot delete a PO that was already sent to supplier."
            )

        po.delete()

        return JsonResponse(
            {
                "success": True,
            },
            status=200,
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": f"There was an error while trying to delete Purchase Order {pk}: {e}",
            }
        )


@require_http_methods(["POST"])
def extract_supplier_quote_data_view(request):
    """
    Extract data from a supplier quote to pre-fill a PO form.
    """
    try:
        # Check if a file was uploaded
        if "quote_file" not in request.FILES:
            return JsonResponse(
                {"success": False, "error": "No quote file uploaded."}, status=400
            )

        quote_file = request.FILES["quote_file"]

        ai_provider = AIProvider.objects.filter(default=True).first()

        logger.info(f"Processing quote with {ai_provider} AI provider")

        purchase_order = PurchaseOrder.objects.create(
            status="draft", order_date=timezone.now().date()
        )

        quote = save_quote_file(purchase_order, quote_file)

        # Create PO from quote
        purchase_order, error = create_po_from_quote(
            purchase_order=purchase_order, quote=quote, ai_provider=ai_provider
        )

        if error:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Error extracting data from quote: {error}",
                },
                status=400,
            )

        # Redirect to the PO form with the PO ID
        redirect_url = reverse(
            "purchasing:purchase_orders_detail", kwargs={"pk": purchase_order.id}
        )
        return redirect(redirect_url)

    except Exception as e:
        logger.exception(f"Error extracting data from quote: {e}")
        return JsonResponse(
            {"success": False, "error": f"Error extracting data from quote: {str(e)}"},
            status=500,
        )


class PurchaseOrderEmailView(APIView):
    """
    API view for generating email links for purchase orders.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, purchase_order_id):
        """
        Generate and return email details for the specified purchase order.

        Args:
            request: The HTTP request
            purchase_order_id: UUID of the purchase order

        Returns:
            Response: Email details if successful
            Response: Error details if unsuccessful
        """
        try:
            purchase_order = get_object_or_404(PurchaseOrder, pk=purchase_order_id)

            email_data = create_purchase_order_email(purchase_order)

            pdf_buffer = create_purchase_order_pdf(purchase_order)
            pdf_content = pdf_buffer.getvalue()
            pdf_buffer.close()

            pdf_base64 = base64.b64encode(pdf_content).decode("utf-8")
            return JsonResponse(
                {
                    "success": True,
                    "mailto_url": email_data["mailto_url"],
                    "email": email_data["email"],
                    "subject": email_data["subject"],
                    "body": email_data["body"],
                    "pdf_content": pdf_base64,
                    "pdf_name": f"po_{purchase_order.po_number}.pdf",
                }
            )
        except ValueError as e:
            logger.warning(
                f"Value error for purchase order {purchase_order_id}: {str(e)}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": str(e),
                },
                status=400,
            )
        except Exception as e:
            logger.exception(
                f"Error generating email for purchase order {purchase_order_id}: {str(e)}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "Could not generate email",
                    "details": str(e),
                },
                status=500,
            )


class PurchaseOrderPDFView(APIView):
    """
    API view for generating and returning PDF documents for purchase orders.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, purchase_order_id):
        """
        Generate and return a PDF for the specified purchase order.

        Args:
            request: The HTTP request
            purchase_order_id: UUID of the purchase order

        Returns:
            FileResponse: PDF file if successful
            Response: Error details if unsuccessful
        """
        try:
            # Retrieve the purchase order
            purchase_order = get_object_or_404(PurchaseOrder, pk=purchase_order_id)

            # Generate the PDF using the service
            pdf_buffer = create_purchase_order_pdf(purchase_order)

            # Configure the response
            filename = f"PO_{purchase_order.po_number}.pdf"

            # Return as inline content or for download based on query parameter
            as_attachment = (
                request.query_params.get("download", "false").lower() == "true"
            )

            # Create the response with the PDF
            response = FileResponse(
                pdf_buffer,
                as_attachment=as_attachment,
                filename=filename,
                content_type="application/pdf",
            )

            # Add content disposition header
            disposition = (
                f'{"attachment" if as_attachment else "inline"}; filename="{filename}"'
            )
            response["Content-Disposition"] = disposition

            return response

        except Exception as e:
            logger.exception(
                f"Error generating PDF for purchase order {purchase_order_id}: {str(e)}"
            )
            return Response(
                {
                    "status": "error",
                    "message": "Could not generate PDF",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
