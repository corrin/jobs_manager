from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0192_add_financial_year_start_month"),
    ]

    operations = [
        migrations.AddField(
            model_name="companydefaults",
            name="job_gp_target_percentage",
            field=models.DecimalField(
                decimal_places=2,
                default=50.0,
                help_text="Target gross profit percentage for jobs",
                max_digits=5,
                verbose_name="Target GP % per Job",
            ),
            preserve_default=False,
        ),
    ]
