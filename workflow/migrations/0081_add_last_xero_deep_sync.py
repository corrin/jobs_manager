from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('workflow', '0080_add_last_xero_sync_to_company_defaults'),
    ]

    operations = [
        migrations.AddField(
            model_name='companydefaults',
            name='last_xero_deep_sync',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="The last time a deep Xero sync was performed (looking back 90 days)",
            ),
        ),
    ]