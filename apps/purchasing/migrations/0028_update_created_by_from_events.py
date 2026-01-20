# Data migration: update created_by from first event where available

from django.db import migrations


def update_created_by_from_first_event(apps, schema_editor):
    """
    Update created_by to use the staff from the first event for each PO.
    Only updates POs that don't already have created_by set.
    """
    PurchaseOrder = apps.get_model("purchasing", "PurchaseOrder")
    PurchaseOrderEvent = apps.get_model("purchasing", "PurchaseOrderEvent")

    for po in PurchaseOrder.objects.filter(created_by__isnull=True):
        first_event = (
            PurchaseOrderEvent.objects.filter(purchase_order=po)
            .order_by("timestamp")
            .first()
        )
        if first_event and first_event.staff_id:
            po.created_by_id = first_event.staff_id
            po.save(update_fields=["created_by_id"])


def reverse_noop(apps, schema_editor):
    """Reverse: no-op since we can't know which were originally from events."""


class Migration(migrations.Migration):

    dependencies = [
        ("purchasing", "0027_add_created_by_to_purchase_order"),
    ]

    operations = [
        migrations.RunPython(update_created_by_from_first_event, reverse_noop),
    ]
