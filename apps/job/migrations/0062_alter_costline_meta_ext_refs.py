from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0061_fix_labour_cost_lines"),
    ]

    operations = [
        migrations.AlterField(
            model_name="costline",
            name="ext_refs",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="External references (e.g., time entry IDs, material IDs)",
            ),
        ),
        migrations.AlterField(
            model_name="costline",
            name="meta",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    "Additional metadata - structure varies by kind (see class docstring)"
                ),
            ),
        ),
    ]
