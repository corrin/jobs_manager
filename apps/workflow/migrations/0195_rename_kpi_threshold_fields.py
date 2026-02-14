from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0194_add_profit_thresholds"),
    ]

    operations = [
        migrations.RenameField(
            model_name="companydefaults",
            old_name="billable_threshold_green",
            new_name="kpi_daily_billable_hours_green",
        ),
        migrations.RenameField(
            model_name="companydefaults",
            old_name="billable_threshold_amber",
            new_name="kpi_daily_billable_hours_amber",
        ),
        migrations.RenameField(
            model_name="companydefaults",
            old_name="daily_gp_target",
            new_name="kpi_daily_gp_target",
        ),
        migrations.RenameField(
            model_name="companydefaults",
            old_name="shop_hours_target_percentage",
            new_name="kpi_daily_shop_hours_percentage",
        ),
        migrations.RenameField(
            model_name="companydefaults",
            old_name="job_gp_target_percentage",
            new_name="kpi_job_gp_target_percentage",
        ),
        migrations.RenameField(
            model_name="companydefaults",
            old_name="profit_threshold_green",
            new_name="kpi_daily_profit_green",
        ),
        migrations.RenameField(
            model_name="companydefaults",
            old_name="profit_threshold_amber",
            new_name="kpi_daily_profit_amber",
        ),
    ]
