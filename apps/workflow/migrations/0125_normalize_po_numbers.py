# Generated migration to normalize PO numbers with leading zeros and reassign non-standard formats
from django.db import IntegrityError, migrations


def normalize_po_numbers(apps, schema_editor):
    PurchaseOrder = apps.get_model("workflow", "PurchaseOrder")

    # Step 1: Normalize PO numbers to have 4-digit leading zeros, skip on error
    for po in PurchaseOrder.objects.all():
        if po.po_number and po.po_number.startswith("PO-"):
            try:
                num_part = po.po_number.split("-")[1]
                if len(num_part) < 4:  # Check if numeric part has less than 4 digits
                    # Pad with leading zeros to 4 digits
                    normalized_num = num_part.zfill(4)
                    po.po_number = f"PO-{normalized_num}"
                    try:
                        po.save()
                    except IntegrityError:
                        # Skip if save fails due to duplicate key
                        continue
            except IndexError:
                # Skip if format is unexpected
                continue

    # Step 2: Reassign non-standard PO numbers to next available number
    # First, find the highest numeric value in use
    highest_num = 0
    for po in PurchaseOrder.objects.all():
        if po.po_number and po.po_number.startswith("PO-"):
            try:
                num = int(po.po_number.split("-")[1])
                highest_num = max(highest_num, num)
            except (IndexError, ValueError):
                continue

    # Now, update records that don't match PO-XXXX format
    for po in PurchaseOrder.objects.all():
        if po.po_number and not (
            po.po_number.startswith("PO-") and len(po.po_number.split("-")[1]) == 4
        ):
            highest_num += 1
            po.po_number = f"PO-{highest_num:04d}"
            po.save()


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0124_companydefaults_billable_threshold_amber_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_po_numbers),
    ]
