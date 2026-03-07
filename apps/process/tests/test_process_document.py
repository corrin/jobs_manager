import pytest

from apps.process.models import ProcessDocument, ProcessDocumentEntry


@pytest.mark.django_db
class TestProcessDocument:
    def test_create_procedure_with_tags(self):
        doc = ProcessDocument.objects.create(
            document_type="procedure",
            title="Drill Press SOP",
            document_number="355",
            tags=["safety", "sop", "machinery"],
            company_name="Morris Sheetmetal",
        )
        assert doc.document_type == "procedure"
        assert "sop" in doc.tags
        assert doc.status == "active"
        assert doc.is_template is False

    def test_create_template_form(self):
        template = ProcessDocument.objects.create(
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
        template = ProcessDocument.objects.create(
            document_type="form",
            title="Ladder Inspection",
            document_number="110",
            is_template=True,
            company_name="Morris Sheetmetal",
        )
        record = ProcessDocument.objects.create(
            document_type="form",
            title="Ladder Inspection",
            status="completed",
            parent_template=template,
            company_name="Morris Sheetmetal",
        )
        assert record.parent_template == template
        assert template.completed_records.count() == 1

    def test_filter_by_tags_contains(self):
        ProcessDocument.objects.create(
            document_type="procedure",
            title="SWP1",
            tags=["safety", "swp"],
            company_name="Test",
        )
        ProcessDocument.objects.create(
            document_type="procedure",
            title="SOP1",
            tags=["sop"],
            company_name="Test",
        )
        swps = ProcessDocument.objects.filter(tags__contains=["swp"])
        assert swps.count() == 1
        assert swps.first().title == "SWP1"

    def test_filter_by_document_type(self):
        ProcessDocument.objects.create(
            document_type="procedure", title="Proc", company_name="Test"
        )
        ProcessDocument.objects.create(
            document_type="form", title="Form", company_name="Test"
        )
        ProcessDocument.objects.create(
            document_type="register", title="Reg", company_name="Test"
        )
        assert ProcessDocument.objects.filter(document_type="procedure").count() == 1
        assert ProcessDocument.objects.filter(document_type="form").count() == 1

    def test_str_representation(self):
        doc = ProcessDocument.objects.create(
            document_type="procedure",
            title="MIG Welding",
            company_name="Test",
        )
        assert "Procedure" in str(doc)
        assert "MIG Welding" in str(doc)


@pytest.mark.django_db
class TestProcessDocumentEntry:
    def test_create_entry(self):
        doc = ProcessDocument.objects.create(
            document_type="register",
            title="Maintenance Log",
            company_name="Test",
        )
        entry = ProcessDocumentEntry.objects.create(
            document=doc,
            entry_date="2026-03-03",
            data={
                "equipment": "Drill Press",
                "action": "Oiled bearings",
                "status": "OK",
            },
        )
        assert entry.document == doc
        assert entry.data["equipment"] == "Drill Press"
        assert doc.entries.count() == 1

    def test_cascade_delete(self):
        doc = ProcessDocument.objects.create(
            document_type="register",
            title="Maintenance Log",
            company_name="Test",
        )
        ProcessDocumentEntry.objects.create(
            document=doc,
            entry_date="2026-03-03",
            data={"note": "test"},
        )
        doc.delete()
        assert ProcessDocumentEntry.objects.count() == 0
