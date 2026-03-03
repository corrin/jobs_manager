from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("job", "0072_add_processdocumententry"),
    ]

    operations = [
        migrations.AddField(
            model_name="processdocument",
            name="form_schema",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="JSON schema defining entry fields for form templates",
            ),
        ),
    ]
