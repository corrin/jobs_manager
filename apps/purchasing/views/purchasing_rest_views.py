"""REST views for purchasing module."""

import logging
from decimal import Decimal

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job
from apps.purchasing.models import PurchaseOrder, Stock
from apps.purchasing.services.delivery_receipt_service import process_delivery_receipt
from apps.purchasing.services.purchasing_rest_service import PurchasingRestService
from apps.purchasing.services.stock_service import consume_stock
from apps.workflow.api.xero.xero import get_xero_items

logger = logging.getLogger(__name__)


class XeroItemList(APIView):
    """Return list of items from Xero."""

    def get(self, request):
        try:
            items = PurchasingRestService.list_xero_items()
            return Response(items)
        except Exception as e:
            logger.error("Error fetching Xero items: %s", e)
            return Response(
                {"error": "Failed to fetch Xero items"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PurchaseOrderListCreateRestView(APIView):
    def get(self, request):
        status_filter = request.query_params.get("status", None)
        data = PurchasingRestService.list_purchase_orders()
        if status_filter:
            data = [po for po in data if po["status"] == status_filter]
        return Response(data)

    def post(self, request):
        po = PurchasingRestService.create_purchase_order(request.data)
        return Response(
            {"id": str(po.id), "po_number": po.po_number},
            status=status.HTTP_201_CREATED,
        )


class PurchaseOrderDetailRestView(APIView):
    """Returns a full PO (including lines)"""

    def get(self, request, pk):
        po = get_object_or_404(PurchaseOrder, id=pk)
        return Response(
            {
                "id": str(po.id),
                "po_number": po.po_number,
                "reference": po.reference,
                "supplier": po.supplier.name if po.supplier else "",
                "supplier_has_xero_id": (
                    po.supplier.xero_contact_id is not None if po.supplier else False
                ),
                "status": po.status,
                "order_date": po.order_date,
                "expected_delivery": po.expected_delivery,
                "lines": [
                    {
                        "id": str(l.id),
                        "item_code": l.item_code,
                        "description": l.description,
                        "quantity": float(l.quantity),
                        "unit_cost": (
                            float(l.unit_cost) if l.unit_cost is not None else None
                        ),
                        "price_tbc": l.price_tbc,
                    }
                    for l in po.po_lines.all()
                ],
                "online_url": po.online_url if po.online_url else None,
                "xero_id": po.xero_id if po.xero_id else None,
            }
        )

    def patch(self, request, pk):
        po = PurchasingRestService.update_purchase_order(pk, request.data)
        return Response({"id": str(po.id), "status": po.status})


class DeliveryReceiptRestView(APIView):
    def post(self, request):
        purchase_order_id = request.data.get("purchase_order_id")
        allocations = request.data.get("allocations", {})

        process_delivery_receipt(purchase_order_id, allocations)
        return Response({"success": True})


class StockListRestView(APIView):
    def get(self, request):
        return Response(PurchasingRestService.list_stock())

    def post(self, request):
        try:
            item = PurchasingRestService.create_stock(request.data)
            return Response({"id": str(item.id)}, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class StockDeactivateRestView(APIView):
    def delete(self, request, stock_id):
        item = get_object_or_404(Stock, id=stock_id)
        if item.is_active:
            item.is_active = False
            item.save()
            return Response({"success": True})
        return Response(
            {"error": "Item is already inactive"}, status=status.HTTP_400_BAD_REQUEST
        )


class StockConsumeRestView(APIView):
    def post(self, request, stock_id):
        job_id = request.data.get("job_id")
        qty = request.data.get("quantity")
        if not all([job_id, qty]):
            return Response(
                {"error": "Missing data"}, status=status.HTTP_400_BAD_REQUEST
            )

        job = get_object_or_404(Job, id=job_id)
        item = get_object_or_404(Stock, id=stock_id)
        try:
            qty_dec = Decimal(str(qty))
        except Exception:
            return Response(
                {"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            consume_stock(item, job, qty_dec, request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True})
