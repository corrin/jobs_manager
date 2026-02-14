# Generated manually

from django.db import migrations, models


def add_attachments_scope(apps, schema_editor):
    """Add accounting.attachments scope to existing XeroToken records."""
    XeroToken = apps.get_model("workflow", "XeroToken")
    for token in XeroToken.objects.all():
        if "accounting.attachments" not in token.scope:
            token.scope = f"{token.scope} accounting.attachments"
            token.save(update_fields=["scope"])


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0193_add_job_gp_target_percentage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="xerotoken",
            name="scope",
            field=models.TextField(
                default="offline_access openid profile email accounting.contacts accounting.transactions accounting.attachments accounting.reports.read accounting.settings accounting.journals.read projects payroll.timesheets payroll.payruns payroll.payslip payroll.employees payroll.settings"
            ),
        ),
        migrations.RunPython(add_attachments_scope, migrations.RunPython.noop),
    ]
