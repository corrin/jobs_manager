# Generated by Django 5.0.6 on 2024-09-24 05:56

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0003_companydefaults_alter_client_xero_contact_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="companydefaults",
            name="company_name",
            field=models.CharField(
                default="Morris Sheetmetal Works", max_length=255, unique=True
            ),
            preserve_default=False,
        ),
    ]
