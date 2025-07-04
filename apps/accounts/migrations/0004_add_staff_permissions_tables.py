# Generated by Django 5.2 on 2025-06-06 11:31

from django.db import migrations, models


# !!!!!
# This migration is meant to be faked in existing dbs. Its only purpose is to create the ManyToMany tables
# (workflow_staff_groups and workflow_staff_user_permissions) when creating a fresh db.
# These tables were removed when Staff model was moved from workflow app to accounts app.
class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_historicalstaff_updated_at_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # Add the ManyToMany fields that Django creates automatically for PermissionsMixin
        migrations.AddField(
            model_name="staff",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                related_name="user_set",
                related_query_name="user",
                to="auth.group",
                verbose_name="groups",
                db_table="workflow_staff_groups",
            ),
        ),
        migrations.AddField(
            model_name="staff",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="user_set",
                related_query_name="user",
                to="auth.permission",
                verbose_name="user permissions",
                db_table="workflow_staff_user_permissions",
            ),
        ),
    ]
