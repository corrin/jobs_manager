import logging
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from django.db import connection, transaction
from django.utils import timezone

from apps.job.enums import MetalType
from apps.job.models import CostLine, CostSet, Job
from apps.purchasing.models import Stock
from apps.workflow.models import CompanyDefaults

logger = logging.getLogger(__name__)


@transaction.atomic
def merge_stock_into(source_stock_id: UUID, target_stock_id: UUID) -> None:
    """
    Merge source stock into target, moving all references then deleting source.

    Moves:
    - child_stock_splits (source_parent_stock FK)
    - CostLine ext_refs['stock_id'] references (JSON update)

    Then deletes the source stock.
    """
    source_str = str(source_stock_id)
    target_str = str(target_stock_id)

    # 1. Move child stock splits (FK)
    Stock.objects.filter(source_parent_stock_id=source_stock_id).update(
        source_parent_stock_id=target_stock_id
    )

    # 2. Update CostLine ext_refs JSON where stock_id matches source
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE job_costline
            SET ext_refs = JSON_SET(ext_refs, '$.stock_id', %s)
            WHERE JSON_EXTRACT(ext_refs, '$.stock_id') = %s
            """,
            [target_str, source_str],
        )

    # 3. Delete the source stock
    Stock.objects.filter(id=source_stock_id).delete()

    logger.info(f"Merged stock {source_stock_id} into {target_stock_id}")


def _normalize(text: Optional[str]) -> str:
    """Return a trimmed, lower-cased string for safe comparisons."""
    return text.strip().lower() if text else ""


def _weighted_average(
    existing_value: Optional[Decimal],
    existing_qty: Decimal,
    incoming_value: Optional[Decimal],
    incoming_qty: Decimal,
) -> Optional[Decimal]:
    """
    Blend two decimal values using their quantities.
    Returns the incoming_value when existing is missing or qty <= 0.
    """
    if incoming_value is None:
        return existing_value

    if existing_value is None or existing_qty <= 0:
        return incoming_value.quantize(Decimal("0.01"))

    total_qty = existing_qty + incoming_qty
    if total_qty <= 0:
        return incoming_value.quantize(Decimal("0.01"))

    blended = (
        (existing_value * existing_qty) + (incoming_value * incoming_qty)
    ) / total_qty
    return blended.quantize(Decimal("0.01"))


def _default_unit_revenue(unit_cost: Decimal) -> Decimal:
    """Derive unit_revenue using the configured materials markup."""
    materials_markup = CompanyDefaults.get_instance().materials_markup
    return (unit_cost * (Decimal("1") + materials_markup)).quantize(Decimal("0.01"))


@transaction.atomic
def upsert_stock_entry(
    *,
    description: str,
    quantity: Decimal,
    unit_cost: Decimal,
    source: str,
    job: Optional[Job] = None,
    metal_type: Optional[str] = None,
    alloy: Optional[str] = None,
    specifics: Optional[str] = None,
    location: Optional[str] = None,
    unit_revenue: Optional[Decimal] = None,
) -> tuple[Stock, bool]:
    """
    Create or merge a stock entry based on its identity.

    Identity keys:
    - job (defaults to stock holding job)
    - source (manual, product_catalog, etc.)
    - description (case-insensitive)
    - metal_type, alloy, specifics, location (normalized strings)

    Returns (stock_item, created_flag).
    """
    quantity = Decimal(str(quantity))
    unit_cost = Decimal(str(unit_cost))
    unit_revenue = Decimal(str(unit_revenue)) if unit_revenue is not None else None

    if quantity <= 0:
        raise ValueError("Quantity must be positive")

    job = job or Stock.get_stock_holding_job()
    metal_type_value = metal_type or MetalType.UNSPECIFIED

    desc_norm = description.strip()
    alloy_norm = _normalize(alloy)
    specifics_norm = _normalize(specifics)
    location_norm = _normalize(location)

    candidates = (
        Stock.objects.select_for_update()
        .filter(
            is_active=True,
            job=job,
            source=source,
            metal_type=metal_type_value,
            description__iexact=desc_norm,
        )
        .order_by("date")
    )

    match: Optional[Stock] = None
    for candidate in candidates:
        if (
            _normalize(candidate.alloy) == alloy_norm
            and _normalize(candidate.specifics) == specifics_norm
            and _normalize(candidate.location) == location_norm
        ):
            match = candidate
            break

    # Calculate default revenue if not provided
    resolved_unit_revenue = (
        unit_revenue if unit_revenue is not None else _default_unit_revenue(unit_cost)
    )

    if match:
        existing_qty = match.quantity
        new_qty = existing_qty + quantity

        match.quantity = new_qty
        match.unit_cost = _weighted_average(
            match.unit_cost, existing_qty, unit_cost, quantity
        )
        match.unit_revenue = _weighted_average(
            match.unit_revenue, existing_qty, resolved_unit_revenue, quantity
        )

        update_fields = ["quantity", "unit_cost", "unit_revenue"]
        if hasattr(match, "updated_at"):
            update_fields.append("updated_at")

        match.save(update_fields=update_fields)

        # Ensure item_code exists for merged records
        if not match.item_code or not match.item_code.strip():
            from apps.workflow.api.xero.stock_sync import generate_item_code

            match.item_code = generate_item_code(match)
            match.save(update_fields=["item_code"])

        logger.info(
            "Merged incoming stock into existing item %s (qty +%s -> %s)",
            match.id,
            quantity,
            new_qty,
        )
        return match, False

    stock_item = Stock.objects.create(
        job=job,
        description=description,
        quantity=quantity,
        unit_cost=unit_cost,
        unit_revenue=resolved_unit_revenue,
        source=source,
        metal_type=metal_type_value,
        alloy=alloy or "",
        specifics=specifics or "",
        location=location or "",
        is_active=True,
    )

    # Parse to enrich metadata + generate deterministic item_code
    try:
        from apps.quoting.services.stock_parser import auto_parse_stock_item

        auto_parse_stock_item(stock_item)
    except Exception:
        logger.exception(
            "Failed to auto-parse stock item %s during upsert; proceeding without parse",
            stock_item.id,
        )

    if not stock_item.item_code or not stock_item.item_code.strip():
        from apps.workflow.api.xero.stock_sync import generate_item_code

        stock_item.item_code = generate_item_code(stock_item)
        stock_item.save(update_fields=["item_code"])

    return stock_item, True


def consume_stock(
    item: Stock,
    job: Job,
    qty: Decimal,
    user: Any,
    unit_cost: Optional[Decimal] = None,
    unit_rev: Optional[Decimal] = None,
    line: Optional[CostLine] = None,
) -> CostLine:
    if qty <= 0:
        raise ValueError("Quantity must be positive")

    with transaction.atomic():
        # Reload with row-level lock to avoid race conditions
        item = Stock.objects.select_for_update().get(id=item.id)

        original_quantity = item.quantity
        item.quantity -= qty

        # Log warnings for negative stock but allow it
        if item.quantity < 0:
            logger.warning(
                f"Stock item {item.id} ({item.description}) went negative: {original_quantity} -> {item.quantity} (consumed {qty})"
            )
        elif item.quantity == 0:
            logger.info(
                f"Stock item {item.id} ({item.description}) fully consumed: {original_quantity} -> 0 (consumed {qty})"
            )

        # Save the new quantity (negative quantities are allowed)
        item.save(update_fields=["quantity"])

        # If no unit cost or revenue is provided, this means the staff didn't override the default values from stock
        if unit_cost is None:
            unit_cost = item.unit_cost

        if unit_rev is None:
            materials_markup = CompanyDefaults.get_instance().materials_markup
            unit_rev = item.unit_cost * (1 + materials_markup)

        # Ensure job has an actual cost set
        if not job.latest_actual:
            actual_cost_set = CostSet.objects.create(
                job=job, kind="actual", rev=1, summary={"cost": 0, "rev": 0, "hours": 0}
            )
            job.latest_actual = actual_cost_set
            job.save(update_fields=["latest_actual"])
            logger.info(f"Created missing actual CostSet for job {job.id}")

        cost_set = job.latest_actual

        if not line:
            cost_line = CostLine.objects.create(
                cost_set=cost_set,
                kind="material",
                desc=item.description,
                quantity=qty,
                unit_cost=unit_cost,
                unit_rev=unit_rev,
                accounting_date=timezone.now().date(),
                ext_refs={"stock_id": str(item.id)},
                meta={
                    "consumed_by": (
                        str(getattr(user, "id", None))
                        if getattr(user, "id", None)
                        else None
                    )
                },
            )
            logger.info(
                "Consumed %s of stock %s for job %s and created new line with id: %s",
                qty,
                item.id,
                job.id,
                cost_line.id,
            )
            return cost_line

        line.approved = True
        line.quantity = qty
        line.desc = item.description
        line.unit_cost = unit_cost
        line.unit_rev = unit_rev
        line.accounting_date = timezone.now().date()
        line.ext_refs = {"stock_id": str(item.id)}
        line.meta = {
            "consumed_by": (
                str(getattr(user, "id", None)) if getattr(user, "id", None) else None
            )
        }

        line.save(
            update_fields=[
                "approved",
                "desc",
                "unit_cost",
                "unit_rev",
                "accounting_date",
                "ext_refs",
                "meta",
            ]
        )
    return line
