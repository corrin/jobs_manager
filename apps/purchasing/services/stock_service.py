import logging
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.job.models import CostLine, Job
from apps.purchasing.models import Stock
from apps.workflow.models import CompanyDefaults

logger = logging.getLogger(__name__)


def consume_stock(item: Stock, job: Job, qty: Decimal, user: Any) -> CostLine:
    if qty <= 0:
        raise ValueError("Quantity must be positive")

    with transaction.atomic():
        # Reload with row-level lock to avoid race conditions
        item = Stock.objects.select_for_update().get(id=item.id)

        if qty > item.quantity:
            raise ValueError("Quantity used exceeds available stock")

        item.quantity -= qty
        if item.quantity <= 0:
            item.is_active = False
            item.save(update_fields=["quantity", "is_active"])
        else:
            item.save(update_fields=["quantity"])

        materials_markup = CompanyDefaults.get_instance().materials_markup
        unit_rev = item.unit_cost * (1 + materials_markup)
        cost_set = job.latest_actual
        cost_line = CostLine.objects.create(
            cost_set=cost_set,
            kind="material",
            desc=f"Consumed: {item.description}",
            quantity=qty,
            unit_cost=item.unit_cost,
            unit_rev=unit_rev,
            ext_refs={"stock_id": str(item.id)},
            meta={"consumed_by": getattr(user, "id", None)},
        )

    logger.info("Consumed %s of stock %s for job %s", qty, item.id, job.id)
    return cost_line
