import json

from django.db import migrations, models


def backfill_quote_number(apps, schema_editor):
    """Populate number from raw_json for existing Quote records."""
    Quote = apps.get_model("accounting", "Quote")
    for quote in Quote.objects.filter(raw_json__isnull=False):
        raw = quote.raw_json
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
        if isinstance(raw, dict):
            quote_number = raw.get("quote_number") or raw.get("QuoteNumber")
            if quote_number:
                quote.number = str(quote_number)
                quote.save(update_fields=["number"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounting", "0004_protect_critical_fks"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="number",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.RunPython(backfill_quote_number, migrations.RunPython.noop),
    ]
