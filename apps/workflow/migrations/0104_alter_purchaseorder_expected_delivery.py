# Generated by Django 5.1.5 on 2025-03-24 08:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0103_companydefaults_starting_po_number"),
    ]

    operations = [
        migrations.AlterField(
            model_name="purchaseorder",
            name="expected_delivery",
            field=models.DateField(blank=True, null=True),
        ),
    ]
