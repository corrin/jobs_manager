# Generated by Django 5.0.6 on 2024-09-16 03:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0005_alter_historicaljob_job_number_alter_job_job_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaljob",
            name="job_name",
            field=models.CharField(default="DEFAULT_NAME", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="job",
            name="job_name",
            field=models.CharField(default="DEFAULT_NAME", max_length=100),
            preserve_default=False,
        ),
    ]
