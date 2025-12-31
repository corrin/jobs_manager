"""Delete PayrollCategory model.

PayrollCategory has been replaced by XeroPayItem, which is synced from Xero.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0187_create_xero_pay_item"),
        ("job", "0062_job_default_xero_pay_item"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PayrollCategory",
        ),
    ]
