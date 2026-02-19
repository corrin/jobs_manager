from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Mapping

from django.core.exceptions import ValidationError

from apps.job.enums import MetalType
from apps.purchasing.models import PurchaseOrderLine, Stock
from apps.workflow.api.xero.stock_sync import generate_item_code


def _build_stock_stub(
    *,
    description: str,
    metal_type: str | None,
    alloy: str | None,
    specifics: str | None,
) -> Stock:
    return Stock(
        id=uuid.uuid4(),
        description=description or "Stock item",
        quantity=Decimal("0"),
        unit_cost=Decimal("0"),
        source="manual",
        metal_type=metal_type or MetalType.UNSPECIFIED,
        alloy=alloy or "",
        specifics=specifics or "",
    )


def ensure_item_code_for_stock(stock: Stock) -> str:
    if stock.item_code and stock.item_code.strip():
        stock.item_code = stock.item_code.strip()
        return stock.item_code
    generated = generate_item_code(stock)
    if not generated or not generated.strip():
        raise ValidationError("Failed to generate item_code for stock item.")
    stock.item_code = generated.strip()
    return stock.item_code


def ensure_item_code_for_po_line(
    line: PurchaseOrderLine, metadata: Mapping[str, str] | None = None
) -> str:
    if line.item_code and line.item_code.strip():
        return line.item_code.strip()

    metadata = metadata or {}
    metal_type = metadata.get("metal_type") or line.metal_type
    alloy = metadata.get("alloy") or line.alloy
    specifics = metadata.get("specifics") or line.specifics
    stub = _build_stock_stub(
        description=line.description,
        metal_type=metal_type,
        alloy=alloy,
        specifics=specifics,
    )
    return ensure_item_code_for_stock(stub)


def ensure_item_code_for_stock_payload(payload: Mapping[str, object]) -> str:
    item_code = str(payload.get("item_code") or "").strip()
    if item_code:
        return item_code

    stub = _build_stock_stub(
        description=str(payload.get("description") or ""),
        metal_type=str(payload.get("metal_type") or MetalType.UNSPECIFIED),
        alloy=str(payload.get("alloy") or ""),
        specifics=str(payload.get("specifics") or ""),
    )
    return ensure_item_code_for_stock(stub)
