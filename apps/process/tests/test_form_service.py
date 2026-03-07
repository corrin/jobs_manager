from unittest.mock import MagicMock, patch

import pytest

from apps.process.models import Form
from apps.process.services.form_service import FormService
from apps.workflow.models import CompanyDefaults


def _make_service():
    """Create a FormService with external dependencies mocked out."""
    with patch("apps.process.services.form_service.GoogleDocsService"):
        service = FormService()
    service.docs_service = MagicMock()
    return service


@pytest.mark.django_db
class TestFormServiceFillTemplate:
    def test_fill_template_creates_record(self):
        template = Form.objects.create(
            document_type="form",
            title="Inspection Form",
            document_number="110",
            tags=["safety", "inspection"],
            is_template=True,
            company_name="Morris Sheetmetal",
        )

        service = _make_service()
        record = service.fill_template(template_id=template.pk)

        assert record.parent_template == template
        assert record.status == "draft"
        assert record.is_template is False
        assert record.document_type == "form"
        assert record.tags == ["safety", "inspection"]
        assert record.company_name == "Morris Sheetmetal"

    def test_fill_template_copies_form_schema(self):
        schema = {
            "fields": [
                {"key": "item", "label": "Item", "type": "text", "required": True},
                {"key": "checked", "label": "Checked", "type": "boolean"},
            ]
        }
        template = Form.objects.create(
            document_type="form",
            title="Checklist",
            is_template=True,
            company_name="Test",
            form_schema=schema,
        )

        service = _make_service()
        record = service.fill_template(template_id=template.pk)

        assert record.form_schema == schema
        assert record.form_schema is not template.form_schema

    def test_fill_non_template_raises(self):
        doc = Form.objects.create(
            document_type="form",
            title="Not a template",
            is_template=False,
            company_name="Test",
        )
        service = _make_service()
        with pytest.raises(ValueError, match="not a template"):
            service.fill_template(template_id=doc.pk)


@pytest.mark.django_db
class TestFormServiceComplete:
    def test_complete_form(self):
        doc = Form.objects.create(
            document_type="form",
            title="Filled Form",
            status="draft",
            company_name="Test",
        )

        service = _make_service()
        result = service.complete_form(doc.pk)

        assert result.status == "completed"
        doc.refresh_from_db()
        assert doc.status == "completed"

    def test_complete_already_completed_raises(self):
        doc = Form.objects.create(
            document_type="form",
            title="Done",
            status="completed",
            company_name="Test",
        )
        service = _make_service()
        with pytest.raises(ValueError, match="already completed"):
            service.complete_form(doc.pk)


@pytest.mark.django_db
class TestFormServiceCreateForm:
    def test_create_form_happy_path(self):
        CompanyDefaults.objects.create(company_name="Morris Sheetmetal")

        service = _make_service()
        doc = service.create_form(
            title="Inspection Checklist",
            document_type="form",
            tags=["safety", "inspection"],
            is_template=True,
            document_number="110",
            form_schema={"fields": [{"key": "item", "type": "text"}]},
        )

        assert doc.document_type == "form"
        assert doc.title == "Inspection Checklist"
        assert doc.tags == ["safety", "inspection"]
        assert doc.is_template is True
        assert doc.document_number == "110"
        assert doc.company_name == "Morris Sheetmetal"
        assert doc.status == "active"
        assert doc.form_schema == {"fields": [{"key": "item", "type": "text"}]}

    def test_create_form_record_gets_draft_status(self):
        CompanyDefaults.objects.create(company_name="Test")

        service = _make_service()
        doc = service.create_form(
            title="Filled checklist",
            document_type="form",
            is_template=False,
        )

        assert doc.status == "draft"

    def test_create_form_register_type(self):
        CompanyDefaults.objects.create(company_name="Test")

        service = _make_service()
        doc = service.create_form(
            title="Chemical Register",
            document_type="register",
        )

        assert doc.document_type == "register"

    def test_create_form_rejects_procedure_type(self):
        service = _make_service()
        with pytest.raises(ValueError, match="form.*register"):
            service.create_form(
                title="Not a form",
                document_type="procedure",
            )
