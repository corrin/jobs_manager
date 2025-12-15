"""Data migration to populate xero_line_item_id from PO raw_json."""

from django.db import migrations


def populate_xero_line_item_ids(apps, schema_editor):
    """
    Populate xero_line_item_id for PurchaseOrderLine records from PO raw_json.

    Matches lines by description (Xero's description) to local lines.
    """
    PurchaseOrder = apps.get_model("purchasing", "PurchaseOrder")
    apps.get_model("purchasing", "PurchaseOrderLine")

    updated_count = 0
    for po in PurchaseOrder.objects.filter(raw_json__isnull=False):
        raw_json = po.raw_json
        if not raw_json or "_line_items" not in raw_json:
            continue

        xero_lines = raw_json.get("_line_items", [])
        if not xero_lines:
            continue

        # Build a list of local lines for this PO (to handle duplicates via pop)
        local_lines = list(po.po_lines.filter(xero_line_item_id__isnull=True))

        for xero_line in xero_lines:
            xero_line_item_id = xero_line.get("_line_item_id")
            xero_description = xero_line.get("_description")

            if not xero_line_item_id or not xero_description:
                continue

            # Find a matching local line by description
            for i, local_line in enumerate(local_lines):
                # Check if descriptions match (Xero description may have job number prefix)
                if local_line.description in xero_description:
                    local_line.xero_line_item_id = xero_line_item_id
                    local_line.save(update_fields=["xero_line_item_id"])
                    updated_count += 1
                    # Pop matched line so duplicates work correctly
                    local_lines.pop(i)
                    break

    print(f"Updated {updated_count} PurchaseOrderLine records with xero_line_item_id")


def reverse_migration(apps, schema_editor):
    """Reverse: clear all xero_line_item_id values."""
    PurchaseOrderLine = apps.get_model("purchasing", "PurchaseOrderLine")
    PurchaseOrderLine.objects.filter(xero_line_item_id__isnull=False).update(
        xero_line_item_id=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ("purchasing", "0018_add_xero_line_item_id"),
    ]

    operations = [
        migrations.RunPython(populate_xero_line_item_ids, reverse_migration),
    ]
