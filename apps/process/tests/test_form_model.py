import pytest

from apps.process.models import Form, FormEntry


@pytest.mark.django_db
class TestForm:
    def test_create_template_form(self):
        template = Form.objects.create(
            document_type="form",
            title="Ladder Inspection Checklist",
            document_number="110",
            tags=["safety", "inspection"],
            is_template=True,
            company_name="Morris Sheetmetal",
        )
        assert template.is_template is True
        assert template.status == "active"

    def test_completed_record_links_to_template(self):
        template = Form.objects.create(
            document_type="form",
            title="Ladder Inspection",
            document_number="110",
            is_template=True,
            company_name="Morris Sheetmetal",
        )
        record = Form.objects.create(
            document_type="form",
            title="Ladder Inspection",
            status="completed",
            parent_template=template,
            company_name="Morris Sheetmetal",
        )
        assert record.parent_template == template
        assert template.completed_records.count() == 1

    def test_filter_by_document_type(self):
        Form.objects.create(document_type="form", title="Form", company_name="Test")
        Form.objects.create(document_type="register", title="Reg", company_name="Test")
        assert Form.objects.filter(document_type="form").count() == 1
        assert Form.objects.filter(document_type="register").count() == 1

    def test_str_representation(self):
        doc = Form.objects.create(
            document_type="form",
            title="Safety Checklist",
            company_name="Test",
        )
        assert "Form" in str(doc)
        assert "Safety Checklist" in str(doc)


@pytest.mark.django_db
class TestFormEntry:
    def test_create_entry(self):
        doc = Form.objects.create(
            document_type="register",
            title="Maintenance Log",
            company_name="Test",
        )
        entry = FormEntry.objects.create(
            form=doc,
            entry_date="2026-03-03",
            data={
                "equipment": "Drill Press",
                "action": "Oiled bearings",
                "status": "OK",
            },
        )
        assert entry.form == doc
        assert entry.data["equipment"] == "Drill Press"
        assert doc.entries.count() == 1

    def test_cascade_delete(self):
        doc = Form.objects.create(
            document_type="register",
            title="Maintenance Log",
            company_name="Test",
        )
        FormEntry.objects.create(
            form=doc,
            entry_date="2026-03-03",
            data={"note": "test"},
        )
        doc.delete()
        assert FormEntry.objects.count() == 0
