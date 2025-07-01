import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List

from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.client.models import Supplier
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Stock

logger = logging.getLogger(__name__)


class PurchasingRestService:
    """Service layer for purchasing REST operations."""

    @staticmethod
    def _get_valid_date(value) -> date:
        """
        Returns a valid date object. If value is None, empty, or invalid, returns today.
        """
        if not value:
            return timezone.now().date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except Exception:
                return timezone.now().date()
        return timezone.now().date()

    @staticmethod
    def list_purchase_orders() -> List[Dict[str, Any]]:
        pos = PurchaseOrder.objects.all().order_by("-created_at")
        return [
            {
                "id": str(po.id),
                "po_number": po.po_number,
                "status": po.status,
                "order_date": po.order_date.isoformat(),
                "supplier": po.supplier.name if po.supplier else "",
            }
            for po in pos
        ]

    @staticmethod
    def create_purchase_order(data: Dict[str, Any]) -> PurchaseOrder:
        supplier_id = data.get("supplier_id")
        supplier = (
            get_object_or_404(Supplier, id=data["supplier_id"]) if supplier_id else None
        )

        order_date = PurchasingRestService._get_valid_date(data.get("order_date"))
        expected_delivery = PurchasingRestService._get_valid_date(
            data.get("expected_delivery")
        )

        po = PurchaseOrder.objects.create(
            supplier=supplier,
            reference=data.get("reference", ""),
            order_date=order_date,
            expected_delivery=expected_delivery,
        )

        for line in data.get("lines", []):
            price_tbc = bool(line.get("price_tbc", False))
            unit_cost = line.get("unit_cost")
            match price_tbc, unit_cost is not None:
                case (True, _):
                    unit_cost = None
                case (False, True):
                    unit_cost = Decimal(str(unit_cost))

            PurchaseOrderLine.objects.create(
                purchase_order=po,
                job_id=line.get("job_id"),
                description=line.get("description", ""),
                quantity=(
                    Decimal(str(line.get("quantity", 0)))
                    if line.get("quantity") is not None
                    else Decimal("0")
                ),
                unit_cost=unit_cost,
                price_tbc=price_tbc,
                item_code=line.get("item_code"),
            )
        return po

    @staticmethod
    def update_purchase_order(po_id: str, data: Dict[str, Any]) -> PurchaseOrder:
        po = get_object_or_404(PurchaseOrder, id=po_id)
        lines_to_delete = data.get("lines_to_delete")
        if lines_to_delete:
            for line_id in lines_to_delete:
                try:
                    line = PurchaseOrderLine.objects.get(id=line_id, purchase_order=po)
                    line.delete()
                except PurchaseOrderLine.DoesNotExist:
                    continue

        for field in ["reference", "expected_delivery", "status"]:
            if field in data:
                setattr(po, field, data[field])

        po.save()

        existing_lines = {str(line.id): line for line in po.po_lines.all()}
        updated_line_ids = set()

        for line_data in data.get("lines", []):
            line_id = line_data.get("id")
            match bool(line_id and str(line_id) in existing_lines):
                case True:
                    # Update existing line
                    line = existing_lines[str(line_id)]
                    if "description" in line_data:
                        line.description = line_data["description"]
                    if "item_code" in line_data:
                        line.item_code = line_data["item_code"]
                    if "quantity" in line_data:
                        line.quantity = Decimal(str(line_data["quantity"]))
                    if "unit_cost" in line_data:
                        value = line_data["unit_cost"]
                        line.unit_cost = (
                            Decimal(str(value)) if value is not None else None
                        )
                    if "price_tbc" in line_data:
                        line.price_tbc = bool(line_data["price_tbc"])
                    line.save()
                    updated_line_ids.add(str(line_id))
                case False:
                    # Create new line if no id
                    PurchaseOrderLine.objects.create(
                        purchase_order=po,
                        job_id=line_data.get("job_id"),
                        description=line_data.get("description", ""),
                        quantity=(
                            Decimal(str(line_data.get("quantity", 0)))
                            if line_data.get("quantity") is not None
                            else Decimal("0")
                        ),
                        unit_cost=(
                            Decimal(str(line_data["unit_cost"]))
                            if line_data.get("unit_cost") is not None
                            else None
                        ),
                        price_tbc=bool(line_data.get("price_tbc", False)),
                        item_code=line_data.get("item_code"),
                    )

        return po

    @staticmethod
    def list_stock() -> List[Dict[str, Any]]:
        items = Stock.objects.filter(is_active=True)
        return [
            {
                "id": str(s.id),
                "description": s.description,
                "quantity": float(s.quantity),
                "unit_cost": float(s.unit_cost),
            }
            for s in items
        ]

    @staticmethod
    def create_stock(data: dict) -> Stock:
        required = ["description", "quantity", "unit_cost", "source"]
        if not all(k in data for k in required):
            raise ValueError(f"Missing required fields")

        return Stock.objects.create(
            job=Stock.get_stock_holding_job(),
            description=data["description"],
            quantity=Decimal(str(data["quantity"])),
            unit_cost=Decimal(str(data["unit_cost"])),
            source=data["source"],
            notes=data.get("notes", ""),
            metal_type=data.get("metal_type", ""),
            alloy=data.get("alloy", ""),
            specifics=data.get("specifics", ""),
            location=data.get("location", ""),
            is_active=True,
        )

    @staticmethod
    def list_xero_items() -> list[dict]:
        from apps.workflow.api.xero.xero import get_xero_items

        cached = cache.get("xero_items")
        if cached is not None:
            return cached
        try:
            raw = get_xero_items()
            items = []
            for i in raw:
                items.append(
                    {
                        "id": i.item_id if i.item_id else None,
                        "code": i.code if i.code else None,
                        "name": i.name if i.name else None,
                        "unit_cost": (
                            i.purchase_details.unit_price
                            if i.purchase_details and i.purchase_details.unit_price
                            else None
                        ),
                    }
                )
            return items
        except Exception as e:
            logger.exception("Failed to fetch Xero items")
            return []
