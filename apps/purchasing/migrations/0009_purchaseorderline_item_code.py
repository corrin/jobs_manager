from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("purchasing", "0008_stock_parsed_at_stock_parser_confidence_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorderline",
            name="item_code",
            field=models.CharField(
                max_length=50,
                null=True,
                blank=True,
                db_index=True,
                help_text="Internal item code for Xero integration",
            ),
        ),
    ]
