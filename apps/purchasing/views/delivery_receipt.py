import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, TemplateView

from apps.job.models import Job
from apps.job.utils import get_active_jobs
from apps.purchasing.models import PurchaseOrder
from apps.purchasing.services.delivery_receipt_service import process_delivery_receipt

logger = logging.getLogger(__name__)


class DeliveryReceiptListView(LoginRequiredMixin, ListView):
    """View to list all purchase orders that can be received."""

    model = PurchaseOrder
    template_name = "purchasing/delivery_receipt_list.html"
    context_object_name = "purchase_orders"

    def get_queryset(self):
        """Return purchase orders that are submitted or partially received."""
        return PurchaseOrder.objects.filter(
            status__in=["submitted", "partially_received"]
        ).order_by("-po_number")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Delivery Receipts"
        return context


class DeliveryReceiptCreateView(LoginRequiredMixin, TemplateView):
    """View to create a delivery receipt for a purchase order."""

    template_name = "purchasing/delivery_receipt_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        purchase_order = get_object_or_404(PurchaseOrder, pk=kwargs["pk"])

        if purchase_order.status not in ["submitted", "partially_received"]:
            raise ValueError("This purchase order cannot be received")

        context["purchase_order"] = purchase_order
        context["title"] = f"Delivery Receipt - {purchase_order.po_number}"

        # Find the job designated for holding general stock by its specific name.
        # Assumes 'create_shop_jobs' guarantees this job exists.
        stock_holding_job = Job.objects.get(name="Worker Admin")
        context["stock_holding_job_id"] = str(stock_holding_job.id)
        context["stock_holding_job_name"] = stock_holding_job.name

        allocatable_jobs = (
            get_active_jobs().exclude(id=stock_holding_job.id).order_by("job_number")
        )
        job_list_for_js = [
            {"id": str(job.id), "name": str(job)} for job in allocatable_jobs
        ]
        job_list_for_js.insert(
            0,
            {
                "id": context["stock_holding_job_id"],
                "name": f"{context['stock_holding_job_name']} (Stock)",
            },
        )
        context["job_list_json"] = json.dumps(job_list_for_js)

        return context

    def post(self, request, *args, **kwargs):
        try:
            logger.info(f"Received POST data keys: {request.POST.keys()}")
            logger.info(
                f"Looking for 'received_quantities', found: {request.POST.get('received_quantities', 'NOT FOUND')}"
            )
            received_quantities = json.loads(
                request.POST.get("received_quantities", "{}")
            )

            logger.info(f"Received quantities data: {received_quantities}")

            transformed_data = {}
            for line_id, line_data in received_quantities.items():
                total_received = line_data.get("total_received", 0)
                job_allocation = line_data.get("job_allocation", 0)
                stock_allocation = line_data.get("stock_allocation", 0)
                job_id = line_data.get("job_id")
                retail_rate = line_data.get("retail_rate", 20)

                allocations = []

                if job_allocation > 0:
                    allocations.append(
                        {
                            "jobId": job_id,
                            "quantity": job_allocation,
                            "retailRate": retail_rate,
                        }
                    )

                if stock_allocation > 0:
                    stock_holding_job = Job.objects.get(name="Worker Admin")
                    allocations.append(
                        {
                            "jobId": str(stock_holding_job.id),
                            "quantity": stock_allocation,
                            "retailRate": retail_rate,
                            "metadata": {
                                "metal_type": line_data.get(
                                    "metal_type", "unspecified"
                                ),
                                "alloy": line_data.get("alloy", ""),
                                "specifics": line_data.get("specifics", ""),
                                "location": line_data.get("location", ""),
                            },
                        }
                    )

                transformed_data[line_id] = {
                    "total_received": total_received,
                    "allocations": allocations,
                }

            logger.info(f"Transformed data: {transformed_data}")
            process_delivery_receipt(kwargs["pk"], transformed_data)
            return JsonResponse({"success": True})
        except Exception as e:
            logger.error(f"Error processing delivery receipt: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)
