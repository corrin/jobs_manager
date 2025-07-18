# Generated by Django 5.0.6 on 2024-09-24 05:49

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyDefaults",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "time_markup",
                    models.DecimalField(decimal_places=2, default=0.3, max_digits=5),
                ),
                (
                    "materials_markup",
                    models.DecimalField(decimal_places=2, default=0.2, max_digits=5),
                ),
                (
                    "charge_out_rate",
                    models.DecimalField(decimal_places=2, default=105.0, max_digits=6),
                ),
                (
                    "wage_rate",
                    models.DecimalField(decimal_places=2, default=32.0, max_digits=6),
                ),
                ("mon_start", models.TimeField(default="07:00")),
                ("mon_end", models.TimeField(default="15:00")),
                ("tue_start", models.TimeField(default="07:00")),
                ("tue_end", models.TimeField(default="15:00")),
                ("wed_start", models.TimeField(default="07:00")),
                ("wed_end", models.TimeField(default="15:00")),
                ("thu_start", models.TimeField(default="07:00")),
                ("thu_end", models.TimeField(default="15:00")),
                ("fri_start", models.TimeField(default="07:00")),
                ("fri_end", models.TimeField(default="15:00")),
            ],
            options={
                "verbose_name": "Company Defaults",
                "verbose_name_plural": "Company Defaults",
                "db_table": "workflow_companydefaults",
            },
        ),
        migrations.AlterField(
            model_name="client",
            name="xero_contact_id",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
