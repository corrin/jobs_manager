"""Data migration to clean up PO line descriptions.

Removes:
- "Price to be confirmed - " prefix
- Job number prefix (will be re-added by xero_description property)

Also re-links job_id if a valid job number is found in the description.
Logs all changes to a JSON file for recovery.
"""

import json
import re
from datetime import datetime

from django.db import migrations


def clean_descriptions(apps, schema_editor):
    """Clean up description prefixes from PO lines."""
    PurchaseOrderLine = apps.get_model("purchasing", "PurchaseOrderLine")
    Job = apps.get_model("job", "Job")

    # Build lookup of job_number -> job for re-linking (convert to string for matching)
    job_by_number = {str(j.job_number): j for j in Job.objects.all()}

    price_tbc_prefix = "Price to be confirmed - "
    job_number_pattern = re.compile(r"^(\d{5}) - ")

    updated_count = 0
    relinked_count = 0
    changes = []

    for line in PurchaseOrderLine.objects.select_related("job", "purchase_order").all():
        original_desc = line.description
        original_job_id = line.job_id
        description = line.description

        # Keep stripping prefixes until no more changes
        changed = True
        while changed:
            changed = False

            # Strip "Price to be confirmed - "
            if description.startswith(price_tbc_prefix):
                description = description[len(price_tbc_prefix) :]
                changed = True

            # Check for job number prefix
            match = job_number_pattern.match(description)
            if match:
                job_number = match.group(1)
                job = job_by_number.get(job_number)

                if job:
                    # Re-link if job_id is NULL
                    if line.job_id is None:
                        line.job_id = job.id
                        relinked_count += 1

                    # Strip if it matches the (now) assigned job
                    if str(line.job_id) == str(job.id):
                        description = description[len(match.group(0)) :]
                        changed = True

        if description != original_desc or line.job_id != original_job_id:
            changes.append(
                {
                    "id": str(line.id),
                    "po": line.purchase_order.po_number,
                    "old_desc": original_desc,
                    "new_desc": description,
                    "old_job_id": str(original_job_id) if original_job_id else None,
                    "new_job_id": str(line.job_id) if line.job_id else None,
                }
            )
            line.description = description
            line.save(update_fields=["description", "job_id"])
            updated_count += 1

    # Write recovery log
    log_file = f"po_line_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w") as f:
        json.dump(changes, f, indent=2)

    print(f"Cleaned {updated_count} PurchaseOrderLine descriptions")
    print(f"Re-linked {relinked_count} job_ids")
    print(f"Recovery log: {log_file}")


def reverse_migration(apps, schema_editor):
    """No reverse - descriptions are cleaner now."""


class Migration(migrations.Migration):

    dependencies = [
        ("purchasing", "0020_add_purchaseorderevent"),
    ]

    operations = [
        migrations.RunPython(clean_descriptions, reverse_migration),
    ]
