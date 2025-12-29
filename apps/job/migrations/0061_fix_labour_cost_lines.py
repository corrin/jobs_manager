from django.db import migrations


def _needs_time_kind(meta: dict) -> bool:
    """Return True when metadata clearly indicates a labour/time entry."""
    if not isinstance(meta, dict):
        return False
    labour_keys = {
        "consumed_by",
        "staff_id",
        "created_from_timesheet",
        "rate_multiplier",
        "is_billable",
        "date",
        "wage_rate",
        "charge_out_rate",
    }
    return any(key in meta for key in labour_keys)


def cast_labour_adjustments_to_time(apps, schema_editor):
    CostLine = apps.get_model("job", "CostLine")
    for cost_line in CostLine.objects.filter(kind="adjust"):
        meta = cost_line.meta or {}
        if _needs_time_kind(meta):
            cost_line.kind = "time"
            # full_clean() runs inside save(), ensuring validators apply.
            cost_line.save(update_fields=["kind", "updated_at"])


def noop_reverse(apps, schema_editor):
    """No-op reverse migration; manual intervention would be required."""


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0060_alter_historicaljob_rejected_flag_and_more"),
    ]

    operations = [
        migrations.RunPython(
            cast_labour_adjustments_to_time,
            noop_reverse,
        ),
    ]
