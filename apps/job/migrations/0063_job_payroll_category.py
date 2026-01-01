"""Add payroll_category FK to Job model."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0185_fix_unpaid_leave_and_remove_posts_to_xero"),
        ("job", "0062_alter_costline_meta_ext_refs"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaljob",
            name="payroll_category",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="Payroll category for leave jobs. NULL for regular work jobs.",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="workflow.payrollcategory",
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="payroll_category",
            field=models.ForeignKey(
                blank=True,
                help_text="Payroll category for leave jobs. NULL for regular work jobs.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="jobs",
                to="workflow.payrollcategory",
            ),
        ),
    ]
