# Generated manually for Google Docs refactor

from django.db import migrations, models


def delete_all_safety_documents(apps, schema_editor):
    """Delete all existing safety documents - feature not yet shipped."""
    SafetyDocument = apps.get_model("job", "SafetyDocument")
    count = SafetyDocument.objects.count()
    SafetyDocument.objects.all().delete()
    if count > 0:
        print(f"    Deleted {count} existing SafetyDocument records")


def noop(apps, schema_editor):
    """No-op for reverse migration."""


class Migration(migrations.Migration):

    dependencies = [
        ("job", "0056_add_safety_document"),
    ]

    operations = [
        # First, delete all existing records
        migrations.RunPython(delete_all_safety_documents, noop),
        # Remove old content fields
        migrations.RemoveField(
            model_name="safetydocument",
            name="status",
        ),
        migrations.RemoveField(
            model_name="safetydocument",
            name="description",
        ),
        migrations.RemoveField(
            model_name="safetydocument",
            name="ppe_requirements",
        ),
        migrations.RemoveField(
            model_name="safetydocument",
            name="tasks",
        ),
        migrations.RemoveField(
            model_name="safetydocument",
            name="additional_notes",
        ),
        migrations.RemoveField(
            model_name="safetydocument",
            name="pdf_file_path",
        ),
        migrations.RemoveField(
            model_name="safetydocument",
            name="context_document_ids",
        ),
        # Add Google Docs reference fields
        migrations.AddField(
            model_name="safetydocument",
            name="google_doc_id",
            field=models.CharField(
                blank=True,
                help_text="Google Docs document ID",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="safetydocument",
            name="google_doc_url",
            field=models.URLField(
                blank=True,
                help_text="URL to edit the document in Google Docs",
            ),
        ),
    ]
