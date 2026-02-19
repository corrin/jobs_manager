from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0191_add_annual_leave_loading"),
    ]

    operations = [
        migrations.AddField(
            model_name="companydefaults",
            name="financial_year_start_month",
            field=models.IntegerField(
                default=4,
                help_text="Month the financial year starts (1=January, 4=April, 7=July, etc.)",
            ),
        ),
    ]
