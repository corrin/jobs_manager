# Generated by Django 5.0.6 on 2024-11-05 21:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0022_alter_historicaljob_description_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicaljob",
            name="contact_phone",
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AlterField(
            model_name="job",
            name="contact_phone",
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]
