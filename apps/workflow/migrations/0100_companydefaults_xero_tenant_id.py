# Generated by Django 5.1.5 on 2025-03-11 08:15

from django.db import migrations, models


def set_tenant_id(apps, schema_editor):
    CompanyDefaults = apps.get_model("workflow", "CompanyDefaults")
    CompanyDefaults.objects.update(
        xero_tenant_id="75e57cfd-302d-4f84-8734-8aae354e76a7"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0096_merge_20250310_2039"),
    ]

    operations = [
        migrations.AddField(
            model_name="companydefaults",
            name="xero_tenant_id",
            field=models.CharField(
                blank=True,
                help_text="The Xero tenant ID to use for this company",
                max_length=100,
                null=True,
            ),
        ),
        migrations.RunPython(set_tenant_id, migrations.RunPython.noop),
    ]
