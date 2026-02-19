"""Fix fully_invoiced for all existing jobs using corrected logic.

Fixed-price jobs should compare invoiced total against quote revenue,
not actual revenue. Also ensures total_invoiced > 0 is required.
"""

from decimal import Decimal

from django.db import migrations
from django.db.models import Sum
from django.db.models.functions import Coalesce


def fix_fully_invoiced(apps, schema_editor):
    """Recalculate fully_invoiced for all jobs using corrected logic."""
    Job = apps.get_model("job", "Job")
    Invoice = apps.get_model("accounting", "Invoice")
    CostLine = apps.get_model("job", "CostLine")

    EXCLUDED_STATUSES = {"VOIDED", "DELETED"}

    for job in Job.objects.select_related("latest_actual", "latest_quote").iterator():
        total_invoiced = Decimal(
            Invoice.objects.filter(job_id=job.id)
            .exclude(status__in=EXCLUDED_STATUSES)
            .aggregate(total=Coalesce(Sum("total_excl_tax"), Decimal("0")))["total"]
        )

        # Determine target amount based on pricing methodology
        # CostSet.total_revenue is a property (not a DB field), so we compute
        # sum(quantity * unit_rev) from CostLines directly.
        if job.pricing_methodology == "fixed_price" and job.latest_quote_id:
            target_amount = Decimal("0")
            for cl in CostLine.objects.filter(cost_set_id=job.latest_quote_id).values(
                "quantity", "unit_rev"
            ):
                target_amount += cl["quantity"] * cl["unit_rev"]
        elif job.latest_actual_id:
            # T&M or fixed-price without quote: use actual revenue
            target_amount = Decimal("0")
            for cl in CostLine.objects.filter(cost_set_id=job.latest_actual_id).values(
                "quantity", "unit_rev"
            ):
                target_amount += cl["quantity"] * cl["unit_rev"]
        else:
            target_amount = Decimal("0")

        new_value = total_invoiced > 0 and total_invoiced >= target_amount
        if job.fully_invoiced != new_value:
            job.fully_invoiced = new_value
            job.save(update_fields=["fully_invoiced"])


class Migration(migrations.Migration):

    dependencies = [
        ("job", "0068_add_completed_at"),
        ("accounting", "0005_quote_number"),
    ]

    operations = [
        migrations.RunPython(fix_fully_invoiced, migrations.RunPython.noop),
    ]
