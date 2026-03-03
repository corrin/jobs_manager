from unittest.mock import MagicMock, patch

import pytest

from apps.job.models import ProcessDocument
from apps.job.services.google_docs_service import GoogleDocResult
from apps.job.services.process_document_service import ProcessDocumentService
from apps.workflow.models import CompanyDefaults


def _make_service():
    """Create a ProcessDocumentService with external dependencies mocked out."""
    with (
        patch("apps.job.services.process_document_service.SafetyAIService"),
        patch("apps.job.services.process_document_service.GoogleDocsService"),
    ):
        service = ProcessDocumentService()
    # Replace docs_service with a fresh mock so callers can set return values
    service.docs_service = MagicMock()
    return service


@pytest.mark.django_db
class TestProcessDocumentServiceFillTemplate:
    def test_fill_template_creates_record(self):
        template = ProcessDocument.objects.create(
            document_type="form",
            title="Inspection Form",
            document_number="110",
            tags=["safety", "inspection"],
            is_template=True,
            company_name="Morris Sheetmetal",
            site_location="Workshop",
        )

        service = _make_service()
        service.docs_service.copy_document.return_value = GoogleDocResult(
            document_id="new-doc-id",
            edit_url="https://docs.google.com/document/d/new-doc-id/edit",
        )

        # Template has no google_doc_id, so copy won't be called
        record = service.fill_template(template_id=template.pk)

        assert record.parent_template == template
        assert record.status == "draft"
        assert record.is_template is False
        assert record.document_type == "form"
        assert record.tags == ["safety", "inspection"]
        assert record.company_name == "Morris Sheetmetal"

    def test_fill_template_copies_google_doc(self):
        template = ProcessDocument.objects.create(
            document_type="form",
            title="Inspection Form",
            is_template=True,
            google_doc_id="template-doc-id",
            company_name="Test",
        )

        service = _make_service()
        service.docs_service.copy_document.return_value = GoogleDocResult(
            document_id="new-doc-id",
            edit_url="https://docs.google.com/document/d/new-doc-id/edit",
        )

        record = service.fill_template(template_id=template.pk)

        service.docs_service.copy_document.assert_called_once()
        assert record.google_doc_id == "new-doc-id"

    def test_fill_template_copies_form_schema(self):
        schema = {
            "fields": [
                {"key": "item", "label": "Item", "type": "text", "required": True},
                {"key": "checked", "label": "Checked", "type": "boolean"},
            ]
        }
        template = ProcessDocument.objects.create(
            document_type="form",
            title="Checklist",
            is_template=True,
            company_name="Test",
            form_schema=schema,
        )

        service = _make_service()
        record = service.fill_template(template_id=template.pk)

        assert record.form_schema == schema
        # Verify it's a copy, not a shared reference
        assert record.form_schema is not template.form_schema

    def test_fill_non_template_raises(self):
        doc = ProcessDocument.objects.create(
            document_type="procedure",
            title="Not a template",
            is_template=False,
            company_name="Test",
        )
        service = _make_service()
        with pytest.raises(ValueError, match="not a template"):
            service.fill_template(template_id=doc.pk)


@pytest.mark.django_db
class TestProcessDocumentServiceComplete:
    def test_complete_document(self):
        doc = ProcessDocument.objects.create(
            document_type="form",
            title="Filled Form",
            status="draft",
            company_name="Test",
        )

        service = _make_service()

        result = service.complete_document(doc.pk)

        assert result.status == "completed"
        doc.refresh_from_db()
        assert doc.status == "completed"

    def test_complete_sets_google_doc_readonly(self):
        doc = ProcessDocument.objects.create(
            document_type="form",
            title="Filled Form",
            status="draft",
            google_doc_id="some-doc-id",
            company_name="Test",
        )

        service = _make_service()

        service.complete_document(doc.pk)

        service.docs_service.set_readonly.assert_called_once_with("some-doc-id")

    def test_complete_already_completed_raises(self):
        doc = ProcessDocument.objects.create(
            document_type="form",
            title="Done",
            status="completed",
            company_name="Test",
        )
        service = _make_service()
        with pytest.raises(ValueError, match="already completed"):
            service.complete_document(doc.pk)


@pytest.mark.django_db
class TestProcessDocumentServiceCreateBlank:
    def test_create_blank_document_happy_path(self):
        CompanyDefaults.objects.create(
            company_name="Morris Sheetmetal",
            gdrive_reference_library_folder_id="folder-123",
        )

        service = _make_service()
        service.docs_service.create_blank_in_folder.return_value = GoogleDocResult(
            document_id="new-doc-id",
            edit_url="https://docs.google.com/document/d/new-doc-id/edit",
        )

        doc = service.create_blank_document(
            document_type="procedure",
            title="How to weld",
            tags=["welding", "safety"],
            is_template=False,
            document_number="301",
            site_location="Workshop",
        )

        assert doc.document_type == "procedure"
        assert doc.title == "How to weld"
        assert doc.tags == ["welding", "safety"]
        assert doc.is_template is False
        assert doc.document_number == "301"
        assert doc.site_location == "Workshop"
        assert doc.company_name == "Morris Sheetmetal"
        assert doc.status == "draft"
        assert doc.google_doc_id == "new-doc-id"
        assert (
            doc.google_doc_url == "https://docs.google.com/document/d/new-doc-id/edit"
        )
        service.docs_service.create_blank_in_folder.assert_called_once_with(
            title="How to weld", folder_id="folder-123"
        )

    def test_create_blank_document_rejects_invalid_type(self):
        service = _make_service()
        with pytest.raises(ValueError, match="Invalid document_type"):
            service.create_blank_document(
                document_type="invalid",
                title="Bad type",
            )

    def test_create_blank_document_rejects_missing_folder_config(self):
        CompanyDefaults.objects.create(
            company_name="Test",
            gdrive_reference_library_folder_id="",
        )

        service = _make_service()
        with pytest.raises(ValueError, match="gdrive_reference_library_folder_id"):
            service.create_blank_document(
                document_type="procedure",
                title="No folder",
            )
