# Generated by Django 5.1.5 on 2025-03-09 07:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0088_merge_20250305_0549'),
    ]

    operations = [
        migrations.AddField(
            model_name='companydefaults',
            name='starting_job_number',
            field=models.IntegerField(default=1, help_text='Helper field to set the starting job number based on the latest paper job'),
        ),
        migrations.AddField(
            model_name='historicaljob',
            name='collected',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalstaff',
            name='password_needs_reset',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='job',
            name='collected',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='staff',
            name='password_needs_reset',
            field=models.BooleanField(default=False),
        ),
    ]
