"""API tests for the procedure and form endpoints."""

from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Staff
from apps.job.models import ProcessDocument


@pytest.fixture
def staff_user(db):
    return Staff.objects.create_user(
        email="worker@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Worker",
        is_office_staff=True,
    )


@pytest.fixture
def api_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


# ─── Procedure API ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProcedureAPI:
    def test_list_safety_procedures(self, api_client):
        ProcessDocument.objects.create(
            document_type="procedure",
            title="Drill Press SOP",
            tags=["safety", "sop"],
            company_name="Test",
        )
        ProcessDocument.objects.create(
            document_type="form",
            title="Inspection Form",
            tags=["safety"],
            company_name="Test",
        )

        resp = api_client.get("/job/rest/procedures/safety/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["title"] == "Drill Press SOP"

    def test_list_training_procedures(self, api_client):
        ProcessDocument.objects.create(
            document_type="procedure",
            title="Induction Plan",
            tags=["training"],
            company_name="Test",
        )
        ProcessDocument.objects.create(
            document_type="procedure",
            title="Safety SOP",
            tags=["safety"],
            company_name="Test",
        )

        resp = api_client.get("/job/rest/procedures/training/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["title"] == "Induction Plan"

    def test_list_reference_procedures(self, api_client):
        ProcessDocument.objects.create(
            document_type="reference",
            title="Org Chart",
            tags=[],
            company_name="Test",
        )

        resp = api_client.get("/job/rest/procedures/reference/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["title"] == "Org Chart"

    def test_detail_excludes_form_schema(self, api_client):
        doc = ProcessDocument.objects.create(
            document_type="procedure",
            title="SWP",
            tags=["safety", "swp"],
            company_name="Test",
            form_schema={"fields": []},
        )

        resp = api_client.get(f"/job/rest/procedures/safety/{doc.pk}/")
        assert resp.status_code == status.HTTP_200_OK
        assert "form_schema" not in resp.data
        assert "google_doc_url" in resp.data
        assert "google_doc_id" in resp.data

    def test_unknown_category_returns_404(self, api_client):
        resp = api_client.get("/job/rest/procedures/nonexistent/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_excludes_form_schema(self, api_client):
        ProcessDocument.objects.create(
            document_type="procedure",
            title="SWP",
            tags=["safety"],
            company_name="Test",
            form_schema={"fields": []},
        )

        resp = api_client.get("/job/rest/procedures/safety/")
        assert resp.status_code == status.HTTP_200_OK
        assert "form_schema" not in resp.data[0]
        assert "google_doc_url" in resp.data[0]

    def test_filter_by_tags(self, api_client):
        ProcessDocument.objects.create(
            document_type="procedure",
            title="SWP1",
            tags=["safety", "swp"],
            company_name="Test",
        )
        ProcessDocument.objects.create(
            document_type="procedure",
            title="SOP1",
            tags=["safety", "sop"],
            company_name="Test",
        )

        resp = api_client.get("/job/rest/procedures/safety/?tags=swp")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["title"] == "SWP1"

    @patch("apps.job.services.process_document_service.ProcessDocumentService")
    def test_create_procedure(self, MockService, api_client):
        doc = ProcessDocument.objects.create(
            document_type="procedure",
            title="New SWP",
            tags=["safety"],
            company_name="Test",
            status="draft",
        )
        MockService.return_value.create_blank_document.return_value = doc

        resp = api_client.post(
            "/job/rest/procedures/safety/",
            {"title": "New SWP"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["title"] == "New SWP"
        MockService.return_value.create_blank_document.assert_called_once()

    def test_update_procedure(self, api_client):
        doc = ProcessDocument.objects.create(
            document_type="procedure",
            title="Old Title",
            tags=["safety"],
            company_name="Test",
        )

        resp = api_client.patch(
            f"/job/rest/procedures/safety/{doc.pk}/",
            {"title": "New Title"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["title"] == "New Title"

    def test_delete_procedure(self, api_client):
        doc = ProcessDocument.objects.create(
            document_type="procedure",
            title="To Delete",
            tags=["safety"],
            company_name="Test",
        )

        resp = api_client.delete(f"/job/rest/procedures/safety/{doc.pk}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not ProcessDocument.objects.filter(pk=doc.pk).exists()


# ─── Form API ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFormAPI:
    def test_list_safety_forms(self, api_client):
        ProcessDocument.objects.create(
            document_type="form",
            title="Ladder Inspection",
            tags=["safety", "inspection"],
            company_name="Test",
        )
        ProcessDocument.objects.create(
            document_type="procedure",
            title="Safety SOP",
            tags=["safety"],
            company_name="Test",
        )

        resp = api_client.get("/job/rest/forms/safety/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["title"] == "Ladder Inspection"

    def test_list_training_forms(self, api_client):
        ProcessDocument.objects.create(
            document_type="form",
            title="Training Record",
            tags=["training"],
            company_name="Test",
        )

        resp = api_client.get("/job/rest/forms/training/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_list_incident_forms(self, api_client):
        ProcessDocument.objects.create(
            document_type="form",
            title="Incident Report",
            tags=["incident"],
            company_name="Test",
        )

        resp = api_client.get("/job/rest/forms/incident/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_list_meeting_forms(self, api_client):
        ProcessDocument.objects.create(
            document_type="form",
            title="Meeting Agenda",
            tags=["meeting"],
            company_name="Test",
        )
        ProcessDocument.objects.create(
            document_type="form",
            title="Admin Form",
            tags=["administration"],
            company_name="Test",
        )

        resp = api_client.get("/job/rest/forms/meeting/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 2

    def test_list_registers(self, api_client):
        ProcessDocument.objects.create(
            document_type="register",
            title="Chemical Register",
            tags=[],
            company_name="Test",
        )

        resp = api_client.get("/job/rest/forms/register/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_detail_excludes_google_doc_fields(self, api_client):
        doc = ProcessDocument.objects.create(
            document_type="form",
            title="Checklist",
            tags=["safety"],
            company_name="Test",
            form_schema={"fields": [{"key": "item", "type": "text"}]},
        )

        resp = api_client.get(f"/job/rest/forms/safety/{doc.pk}/")
        assert resp.status_code == status.HTTP_200_OK
        assert "form_schema" in resp.data
        assert "google_doc_url" not in resp.data
        assert "google_doc_id" not in resp.data

    def test_unknown_category_returns_404(self, api_client):
        resp = api_client.get("/job/rest/forms/nonexistent/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_entry_guard_rejects_procedure_document(self, api_client):
        doc = ProcessDocument.objects.create(
            document_type="procedure",
            title="SOP",
            tags=["safety"],
            company_name="Test",
        )

        resp = api_client.post(
            f"/job/rest/forms/safety/{doc.pk}/entries/",
            {"entry_date": "2026-03-07", "data": {"note": "test"}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "form or register" in resp.data["error"]

    def test_entry_allowed_for_form_document(self, api_client):
        doc = ProcessDocument.objects.create(
            document_type="form",
            title="Checklist",
            tags=["safety"],
            company_name="Test",
        )

        resp = api_client.post(
            f"/job/rest/forms/safety/{doc.pk}/entries/",
            {"entry_date": "2026-03-07", "data": {"note": "test"}},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_entry_allowed_for_register_document(self, api_client):
        doc = ProcessDocument.objects.create(
            document_type="register",
            title="Chemical Register",
            tags=[],
            company_name="Test",
        )

        resp = api_client.post(
            f"/job/rest/forms/register/{doc.pk}/entries/",
            {"entry_date": "2026-03-07", "data": {"chemical": "acetone"}},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    @patch("apps.job.services.process_document_service.ProcessDocumentService")
    def test_create_form(self, MockService, api_client):
        doc = ProcessDocument.objects.create(
            document_type="form",
            title="New Checklist",
            tags=["safety"],
            company_name="Test",
            status="draft",
            form_schema={"fields": [{"key": "item", "type": "text"}]},
        )
        MockService.return_value.create_form_document.return_value = doc

        resp = api_client.post(
            "/job/rest/forms/safety/",
            {
                "title": "New Checklist",
                "form_schema": {"fields": [{"key": "item", "type": "text"}]},
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["title"] == "New Checklist"
        assert resp.data["form_schema"] == {"fields": [{"key": "item", "type": "text"}]}
        MockService.return_value.create_form_document.assert_called_once()

    def test_update_form(self, api_client):
        doc = ProcessDocument.objects.create(
            document_type="form",
            title="Old Form",
            tags=["safety"],
            company_name="Test",
        )

        resp = api_client.patch(
            f"/job/rest/forms/safety/{doc.pk}/",
            {"title": "Updated Form"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["title"] == "Updated Form"

    def test_delete_form(self, api_client):
        doc = ProcessDocument.objects.create(
            document_type="form",
            title="To Delete",
            tags=["safety"],
            company_name="Test",
        )

        resp = api_client.delete(f"/job/rest/forms/safety/{doc.pk}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not ProcessDocument.objects.filter(pk=doc.pk).exists()


# ─── Removed endpoint ─────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRemovedEndpoints:
    def test_process_documents_endpoint_removed(self, api_client):
        resp = api_client.get("/job/rest/process-documents/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_sop_list_endpoint_removed(self, api_client):
        resp = api_client.get("/job/rest/sop/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_swp_list_endpoint_removed(self, api_client):
        resp = api_client.get("/job/rest/swp/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
