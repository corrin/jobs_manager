from django.db import migrations


def normalize_wage_rate_multiplier(apps, schema_editor):
    CostLine = apps.get_model("job", "CostLine")

    for cost_line in CostLine.objects.filter(kind="time").iterator():
        meta = cost_line.meta or {}
        if not isinstance(meta, dict):
            continue
        if "rate_multiplier" not in meta:
            continue

        if "wage_rate_multiplier" not in meta:
            meta["wage_rate_multiplier"] = meta["rate_multiplier"]
        meta.pop("rate_multiplier", None)
        CostLine.objects.filter(id=cost_line.id).update(meta=meta)


def noop_reverse(apps, schema_editor):
    """No-op reverse migration; normalization is one-way."""


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0062_alter_costline_meta_ext_refs"),
    ]

    operations = [
        migrations.RunPython(normalize_wage_rate_multiplier, noop_reverse),
    ]
