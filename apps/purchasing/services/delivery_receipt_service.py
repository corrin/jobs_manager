import logging
from decimal import Decimal, InvalidOperation
from typing import Dict

from django.db import transaction
from django.db.models import F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.job.models import CostLine, CostSet, Job
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Stock
from apps.workflow.models.company_defaults import CompanyDefaults

logger = logging.getLogger(__name__)


class DeliveryReceiptValidationError(ValueError):
    """Raised when receipt allocation validation fails."""


def _to_decimal(value, *, field_label: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise DeliveryReceiptValidationError(
            f"Invalid decimal format for {field_label}."
        )
    if d < 0:
        raise DeliveryReceiptValidationError(
            f"Negative value not allowed for {field_label}."
        )
    return d


def _load_po_and_lines(
    purchase_order_id: str, line_allocations: Dict
) -> tuple[PurchaseOrder, dict[str, PurchaseOrderLine]]:
    po = PurchaseOrder.objects.select_related("supplier").get(id=purchase_order_id)
    logger.debug("Found PO %s", po.po_number)

    requested_ids = set(line_allocations.keys())
    lines = {
        str(line.id): line
        for line in PurchaseOrderLine.objects.filter(
            id__in=requested_ids, purchase_order=po
        )
    }
    if len(lines) != len(requested_ids):
        missing = requested_ids - set(lines.keys())
        raise DeliveryReceiptValidationError(
            f"Invalid or mismatched PurchaseOrderLine IDs provided: {missing}"
        )
    return po, lines


def _load_jobs(line_allocations: Dict) -> dict[str, Job]:
    job_ids: set[str] = set()
    for line_data in line_allocations.values():
        for alloc in line_data.get("allocations", []):
            jid = alloc.get("job_id")
            if jid:
                job_ids.add(str(jid))
    jobs = {str(j.id): j for j in Job.objects.filter(id__in=job_ids)}
    if len(jobs) != len(job_ids):
        missing = job_ids - set(jobs.keys())
        raise DeliveryReceiptValidationError(
            f"Invalid Job IDs provided in allocations: {missing}"
        )
    return jobs


def _validate_and_prepare_allocations(
    line: PurchaseOrderLine,
    line_data: dict,
    jobs_by_id: dict[str, Job],
) -> tuple[Decimal, list[dict]]:
    """
    Returns (total_received, prepared_allocations).
    Each prepared allocation = {"job": Job, "quantity": Decimal, "metadata": dict, "retail_rate_pct": Decimal}
    """
    total_received = _to_decimal(
        line_data.get("total_received", 0), field_label=f"line {line.id} total_received"
    )

    prepared: list[dict] = []
    alloc_sum = Decimal("0")

    for alloc in line_data.get("allocations", []):
        qty = _to_decimal(
            alloc.get("quantity", 0), field_label=f"line {line.id} allocation quantity"
        )
        if qty == 0:
            continue

        job_id = str(alloc.get("job_id"))
        if not job_id or job_id == "None" or job_id not in jobs_by_id:
            raise DeliveryReceiptValidationError(
                f"Invalid or missing job_id for non-zero allocation on line {line.id}."
            )

        try:
            defaults = CompanyDefaults.get_instance()
            default_retail_rate_pct = defaults.materials_markup * 100
        except Exception as e:
            raise DeliveryReceiptValidationError(
                f"Company defaults not configured: {str(e)}"
            )

        retail_rate_pct = Decimal(str(alloc.get("retailRate", default_retail_rate_pct)))

        prepared.append(
            {
                "job": jobs_by_id[job_id],
                "quantity": qty,
                "metadata": alloc.get("metadata", {}),
                "retail_rate_pct": retail_rate_pct,
            }
        )
        alloc_sum += qty

    # Totals must match (allow tiny tolerance, can be refactored)
    if abs(alloc_sum - total_received) > Decimal("0.001"):
        raise DeliveryReceiptValidationError(
            f"Allocation mismatch for line '{line.description}' (id {line.id}). "
            f"Total Received={total_received}, Sum of Allocations={alloc_sum}."
        )

    return total_received, prepared


def _delete_previous_stock_for_line(line: PurchaseOrderLine) -> None:
    deleted_count, _ = Stock.objects.filter(
        source="purchase_order", source_purchase_order_line=line
    ).delete()
    if deleted_count:
        logger.debug(
            "Deleted %s existing stock entries for line %s.", deleted_count, line.id
        )


def _ensure_actual_costset(job: Job) -> CostSet:
    if job.latest_actual:
        return job.latest_actual
    cs = CostSet.objects.create(job=job, kind="actual", rev=1)
    job.latest_actual = cs
    job.save(update_fields=["latest_actual"])
    logger.debug("Created missing actual CostSet for job %s", job.id)
    return cs


def _create_stock_from_allocation(
    purchase_order: PurchaseOrder,
    line: PurchaseOrderLine,
    job: Job,
    qty: Decimal,
    metadata: dict,
    retail_rate_pct: Decimal,
) -> Stock:
    retail_rate = (Decimal(str(retail_rate_pct)) / Decimal("100")).quantize(
        Decimal("0.0001")
    )

    stock = Stock.objects.create(
        job=job,
        description=line.description,
        quantity=qty,
        unit_cost=line.unit_cost or Decimal("0.00"),
        retail_rate=retail_rate,
        metal_type=metadata.get("metal_type", line.metal_type or "unspecified"),
        alloy=metadata.get("alloy", line.alloy or ""),
        specifics=metadata.get("specifics", line.specifics or ""),
        location=metadata.get("location", line.location or ""),
        date=timezone.now(),
        source="purchase_order",
        source_purchase_order_line=line,
        notes=f"Received from PO {purchase_order.po_number}",
    )

    # Parse extra metadata
    from apps.quoting.services.stock_parser import auto_parse_stock_item

    auto_parse_stock_item(stock)

    logger.info(
        "Created Stock %s for line %s, job %s, qty %s.", stock.id, line.id, job.id, qty
    )
    return stock


def _create_costline_from_allocation(
    purchase_order: PurchaseOrder,
    line: PurchaseOrderLine,
    job: Job,
    qty: Decimal,
    retail_rate_pct: Decimal,
) -> CostLine:
    # Convert percent to decimal for computation
    r = (Decimal(str(retail_rate_pct)) / Decimal("100")).quantize(Decimal("0.0001"))
    try:
        unit_revenue = (line.unit_cost or Decimal("0.00")) * (Decimal("1") + r)
    except TypeError:
        raise DeliveryReceiptValidationError(
            f"Price not confirmed for line {line.id}; cannot create material cost."
        )

    cs = _ensure_actual_costset(job)
    cl = CostLine.objects.create(
        cost_set=cs,
        kind="material",
        desc=line.description,
        quantity=qty,
        unit_cost=line.unit_cost,
        unit_rev=unit_revenue,
        ext_refs={
            "purchase_order_line_id": str(line.id),
            "purchase_order_id": str(purchase_order.id),
        },
        meta={
            "source": "delivery_receipt",
            "retail_rate": float(r),
            "po_number": purchase_order.po_number,
        },
    )
    logger.info(
        "Created CostLine %s for line %s, job %s, qty %s, retail rate %.2f%%.",
        cl.id,
        line.id,
        job.id,
        qty,
        float(retail_rate_pct),
    )
    return cl


def _recompute_po_status(po: PurchaseOrder) -> None:
    totals = po.po_lines.aggregate(
        ordered=Coalesce(Sum("quantity"), Value(Decimal("0"))),
        received=Coalesce(Sum("received_quantity"), Value(Decimal("0"))),
    )
    ordered, received = totals["ordered"], totals["received"]

    if received <= 0 and po.status != "deleted":
        new_status = "submitted"
    elif received < ordered:
        new_status = "partially_received"
    else:
        new_status = "fully_received"

    if new_status != po.status:
        po.status = new_status
        po.save(update_fields=["status"])
        logger.debug("Updated PO %s status to %s", po.po_number, po.status)
    else:
        logger.debug("PO %s status unchanged: %s", po.po_number, po.status)


def process_delivery_receipt(purchase_order_id: str, line_allocations: dict) -> bool:
    """
    Process a delivery receipt:
      1) Validate PO, lines, jobs, and per-line allocations
      2) For each line: delete prior Stock, increment received_quantity, create Stock/CostLines
      3) Recompute PO status
    SRP: this service only validates and persists receipt effects.
    It does NOT generate Xero item codes or push data to Xero.
    """
    logger.info("Starting delivery receipt processing for PO ID: %s", purchase_order_id)
    logger.debug("Received line_allocations: %s", line_allocations)

    STOCK_HOLDING_JOB_ID = Stock.get_stock_holding_job().id

    try:
        with transaction.atomic():
            po, lines_by_id = _load_po_and_lines(purchase_order_id, line_allocations)
            jobs_by_id = _load_jobs(line_allocations)

            # Warn but continue on unexpected status (upstream should prevent)
            if po.status not in ("submitted", "partially_received", "fully_received"):
                logger.warning(
                    "Processing PO %s with unexpected status: %s",
                    po.po_number,
                    po.status,
                )

            # Per-line processing
            for line_id, data in line_allocations.items():
                line = lines_by_id[str(line_id)]
                logger.debug("Processing line %s (%s)", line.id, line.description)

                total_received, prepared_allocs = _validate_and_prepare_allocations(
                    line=line,
                    line_data=data,
                    jobs_by_id=jobs_by_id,
                )

                # Delete prior stock entries created from this line
                _delete_previous_stock_for_line(line)

                # Increment received_quantity atomically
                PurchaseOrderLine.objects.filter(id=line.id).update(
                    received_quantity=F("received_quantity") + total_received
                )
                line.refresh_from_db(fields=["received_quantity"])
                logger.debug(
                    "Added %s to line %s received_quantity → now %s",
                    total_received,
                    line.id,
                    line.received_quantity,
                )

                # Materialize allocations
                for alloc in prepared_allocs:
                    job = alloc["job"]
                    qty = alloc["quantity"]
                    retail_rate_pct = alloc["retail_rate_pct"]

                    if str(job.id) == str(STOCK_HOLDING_JOB_ID):
                        _create_stock_from_allocation(
                            purchase_order=po,
                            line=line,
                            job=job,
                            qty=qty,
                            metadata=alloc.get("metadata", {}),
                            retail_rate_pct=retail_rate_pct,
                        )
                    else:
                        _create_costline_from_allocation(
                            purchase_order=po,
                            line=line,
                            job=job,
                            qty=qty,
                            retail_rate_pct=retail_rate_pct,
                        )

            _recompute_po_status(po)

            logger.info(
                "Successfully processed delivery receipt for PO %s", po.po_number
            )
            return True

    except DeliveryReceiptValidationError:
        # Let DRF/view layer convert to proper 4xx; message already specific
        logger.exception(
            "Validation Error processing delivery receipt for PO %s", purchase_order_id
        )
        raise
    except PurchaseOrder.DoesNotExist:
        logger.exception(
            "PO %s not found during delivery receipt processing", purchase_order_id
        )
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error processing delivery receipt for PO %s: %s",
            purchase_order_id,
            str(e),
        )
        raise
