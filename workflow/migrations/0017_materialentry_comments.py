# Generated by Django 5.0.6 on 2024-10-01 22:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0016_materialentry_item_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="materialentry",
            name="comments",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
