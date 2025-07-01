# Generated manually
import logging

from django.db import migrations

logger = logging.getLogger("xero")


def populate_merge_fields(apps, schema_editor):
    """
    Process all existing clients to populate the new merge tracking fields
    from their raw_json data.
    """
    Client = apps.get_model("client", "Client")

    updated_count = 0
    archived_count = 0
    merged_count = 0

    # First pass: extract archived and merge info from raw_json
    for client in Client.objects.all():
        if not client.raw_json:
            continue

        raw_json = client.raw_json
        updated = False

        # Check for archived status
        contact_status = raw_json.get("_contact_status", "ACTIVE")
        if contact_status == "ARCHIVED" and not client.xero_archived:
            client.xero_archived = True
            archived_count += 1
            updated = True

        # Check for merge information
        merged_to_contact_id = raw_json.get("_merged_to_contact_id")
        if merged_to_contact_id and not client.xero_merged_into_id:
            client.xero_merged_into_id = merged_to_contact_id
            merged_count += 1
            updated = True

        if updated:
            client.save()
            updated_count += 1

    logger.info(f"Migration: Updated {updated_count} clients with merge fields")
    logger.info(f"  - {archived_count} archived clients found")
    logger.info(f"  - {merged_count} clients with merge information")

    # Second pass: resolve merge references
    resolved_count = 0

    for client in Client.objects.filter(
        xero_merged_into_id__isnull=False, merged_into__isnull=True
    ):
        # Find the client this was merged into
        merged_into_client = Client.objects.filter(
            xero_contact_id=client.xero_merged_into_id
        ).first()

        if merged_into_client:
            client.merged_into = merged_into_client
            client.save()
            resolved_count += 1
            logger.info(f"Resolved merge: {client.name} -> {merged_into_client.name}")

    logger.info(f"Migration: Resolved {resolved_count} merge references")


def reverse_populate_merge_fields(apps, schema_editor):
    """
    Clear the merge fields (reverse migration).
    """
    Client = apps.get_model("client", "Client")

    # Clear all merge-related fields
    Client.objects.update(
        xero_archived=False, xero_merged_into_id=None, merged_into=None
    )


class Migration(migrations.Migration):
    dependencies = [
        ("client", "0003_add_xero_merge_tracking"),
    ]

    operations = [
        migrations.RunPython(
            populate_merge_fields,
            reverse_populate_merge_fields,
        ),
    ]
