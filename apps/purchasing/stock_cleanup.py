"""Utilities for merging duplicate stock entries."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.purchasing.models import Stock


def _select_canonical(stocks: Iterable[Stock], *, prefer_latest: bool = True) -> Stock:
    """
    Choose the canonical stock entry from a group.
    Preference order:
        1. Has xero_id
        2. Non-zero quantity
        3. Non-zero unit_cost
        4. Latest date (if prefer_latest) else earliest
    """

    def key(stock: Stock):
        return (
            1 if stock.xero_id else 0,
            1 if stock.quantity not in (None, Decimal("0")) else 0,
            1 if stock.unit_cost not in (None, Decimal("0")) else 0,
            stock.date if prefer_latest else -stock.date.timestamp(),
            stock.pk,
        )

    return max(stocks, key=key)


def consolidate_duplicate_stock(*, dry_run: bool = False) -> dict[str, int]:
    """
    Merge duplicate Stock rows referencing the same purchase order line.

    Args:
        dry_run: If True, only log actions without persisting.

    Returns:
        Dict with summary counts.
    """
    logger = logging.getLogger("purchasing.stock_cleanup")
    duplicate_lines = list(
        Stock.objects.filter(is_active=True, source_purchase_order_line__isnull=False)
        .values("source_purchase_order_line")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .values_list("source_purchase_order_line", flat=True)
    )

    merged_groups = 0
    deactivated_items = 0

    if not duplicate_lines:
        logger.info("No duplicate stock entries detected.")
        return {"groups": 0, "deactivated": 0}

    logger.info(
        "Found %s purchase order lines with duplicate stock.", len(duplicate_lines)
    )

    for line_id in duplicate_lines:
        with transaction.atomic():
            stocks = list(
                Stock.objects.select_for_update()
                .filter(is_active=True, source_purchase_order_line_id=str(line_id))
                .order_by("date", "id")
            )
            if len(stocks) <= 1:
                continue

            merged_groups += 1
            canonical = _select_canonical(stocks)
            duplicates = [s for s in stocks if s.pk != canonical.pk]

            logger.info(
                "Merging %s duplicate stock items into %s for PO line %s.",
                len(duplicates),
                canonical.id,
                line_id,
            )

            total_quantity = sum((s.quantity or Decimal("0")) for s in stocks)

            def choose_value(getter):
                for stock in [canonical] + duplicates:
                    value = getter(stock)
                    if value not in (None, "", Decimal("0")):
                        return value
                return getter(canonical)

            new_unit_cost = choose_value(lambda s: s.unit_cost)
            new_unit_revenue = choose_value(lambda s: s.unit_revenue)
            new_metal_type = choose_value(lambda s: s.metal_type)
            new_alloy = choose_value(lambda s: s.alloy)
            new_specifics = choose_value(lambda s: s.specifics)
            new_location = choose_value(lambda s: s.location)
            new_notes_parts = [
                canonical.notes or "",
                f"Merged duplicates on {timezone.now().isoformat()}",
            ]
            for dup in duplicates:
                new_notes_parts.append(
                    f"[merged {dup.id} qty={dup.quantity} cost={dup.unit_cost}]"
                )

            if not dry_run:
                canonical.quantity = total_quantity
                canonical.unit_cost = new_unit_cost
                canonical.unit_revenue = new_unit_revenue
                canonical.metal_type = new_metal_type
                canonical.alloy = new_alloy
                canonical.specifics = new_specifics
                canonical.location = new_location
                canonical.notes = "\n".join(part for part in new_notes_parts if part)
                canonical.save(
                    update_fields=[
                        "quantity",
                        "unit_cost",
                        "unit_revenue",
                        "metal_type",
                        "alloy",
                        "specifics",
                        "location",
                        "notes",
                        "updated_at",
                    ]
                )

                for dup in duplicates:
                    dup.is_active = False
                    dup.xero_id = None
                    dup.save(update_fields=["is_active", "xero_id", "updated_at"])
                    deactivated_items += 1

    logger.info(
        "Duplicate stock cleanup complete. Groups processed: %s, duplicates deactivated: %s.",
        merged_groups,
        deactivated_items,
    )

    return {"groups": merged_groups, "deactivated": deactivated_items}
