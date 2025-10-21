import logging
from decimal import Decimal
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from apps.job.models import CostLine, CostSet, Job
from apps.purchasing.models import Stock
from apps.workflow.models import CompanyDefaults

logger = logging.getLogger(__name__)


def consume_stock(
    item: Stock,
    job: Job,
    qty: Decimal,
    user: Any,
    unit_cost: Optional[Decimal] = None,
    unit_rev: Optional[Decimal] = None,
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

    logger.info("Consumed %s of stock %s for job %s", qty, item.id, job.id)
    return cost_line
