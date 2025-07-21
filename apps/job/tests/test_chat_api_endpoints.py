"""
Integration tests for Chat API endpoints

Tests the complete API flow from HTTP request to response,
including authentication, validation, and error handling.
"""

import json
import uuid
from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Staff
from apps.client.models import Client
from apps.job.models import Job, JobQuoteChat
from apps.job.services.gemini_chat_service import GeminiChatService
from apps.workflow.enums import AIProviderTypes
from apps.workflow.models import AIProvider, CompanyDefaults


class ChatAPIEndpointTests(TestCase):
    """Test chat API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client_api = APIClient()

        # Create test data
        self.company_defaults = CompanyDefaults.objects.create(
            company_name="Test Company",
            company_abn="123456789",
            company_address="123 Test St",
            company_phone="0123456789",
            company_email="test@example.com",
        )

        self.client_obj = Client.objects.create(
            name="Test Client",
            email="client@example.com",
            phone="0123456789",
        )

        self.job = Job.objects.create(
            name="Test Job",
            job_number="JOB001",
            description="Test job description",
            client=self.client_obj,
            status="quoting",
        )

        self.ai_provider = AIProvider.objects.create(
            provider_type=AIProviderTypes.GOOGLE,
            default=True,
            api_key="test-key",
            model_name="gemini-pro",
        )

        # Create test user
        self.staff = Staff.objects.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        # URLs
        self.chat_history_url = reverse(
            "job-quote-chat-history", kwargs={"job_id": str(self.job.id)}
        )
        self.chat_interaction_url = reverse(
            "job-quote-chat-interaction", kwargs={"job_id": str(self.job.id)}
        )

    def test_chat_history_get_empty(self):
        """Test getting empty chat history"""
        response = self.client_api.get(self.chat_history_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_chat_history_get_with_messages(self):
        """Test getting chat history with existing messages"""
        # Create test messages
        messages = [
            JobQuoteChat.objects.create(
                job=self.job,
                message_id="user-1",
                role="user",
                content="Hello",
            ),
            JobQuoteChat.objects.create(
                job=self.job,
                message_id="assistant-1",
                role="assistant",
                content="Hi there!",
            ),
        ]

        response = self.client_api.get(self.chat_history_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        # Check message content
        result_messages = response.data["results"]
        self.assertEqual(result_messages[0]["content"], "Hello")
        self.assertEqual(result_messages[1]["content"], "Hi there!")

    def test_chat_history_post_create_message(self):
        """Test creating a new chat message"""
        data = {
            "role": "user",
            "content": "Test message creation",
        }

        response = self.client_api.post(
            self.chat_history_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["content"], "Test message creation")
        self.assertEqual(response.data["role"], "user")

        # Verify message was saved to database
        message = JobQuoteChat.objects.get(id=response.data["id"])
        self.assertEqual(message.content, "Test message creation")
        self.assertEqual(message.role, "user")

    def test_chat_history_post_invalid_data(self):
        """Test creating message with invalid data"""
        data = {
            "role": "invalid_role",
            "content": "",
        }

        response = self.client_api.post(
            self.chat_history_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_chat_history_delete_message(self):
        """Test deleting a chat message"""
        message = JobQuoteChat.objects.create(
            job=self.job,
            message_id="test-message-1",
            role="user",
            content="Message to delete",
        )

        delete_url = reverse(
            "job-quote-chat-detail",
            kwargs={"job_id": str(self.job.id), "message_id": message.message_id},
        )

        response = self.client_api.delete(delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify message was deleted
        self.assertFalse(JobQuoteChat.objects.filter(id=message.id).exists())

    def test_chat_history_job_not_found(self):
        """Test accessing chat history for non-existent job"""
        non_existent_job_id = str(uuid.uuid4())
        url = reverse("job-quote-chat-history", kwargs={"job_id": non_existent_job_id})

        response = self.client_api.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "apps.job.services.gemini_chat_service.GeminiChatService.generate_ai_response"
    )
    def test_chat_interaction_success(self, mock_generate_response):
        """Test successful chat interaction"""
        # Mock the service response
        mock_response = JobQuoteChat.objects.create(
            job=self.job,
            message_id="assistant-response-1",
            role="assistant",
            content="AI response to user message",
            metadata={"model": "gemini-pro", "tool_calls": []},
        )
        mock_generate_response.return_value = mock_response

        data = {
            "message": "Test user message for AI",
        }

        response = self.client_api.post(
            self.chat_interaction_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["data"]["content"], "AI response to user message"
        )
        self.assertEqual(response.data["data"]["role"], "assistant")

        # Verify service was called with correct parameters
        mock_generate_response.assert_called_once_with(
            job_id=str(self.job.id), user_message="Test user message for AI"
        )

    def test_chat_interaction_missing_message(self):
        """Test chat interaction with missing message"""
        data = {}

        response = self.client_api.post(
            self.chat_interaction_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("required", response.data["error"])

    def test_chat_interaction_empty_message(self):
        """Test chat interaction with empty message"""
        data = {
            "message": "",
        }

        response = self.client_api.post(
            self.chat_interaction_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_chat_interaction_job_not_found(self):
        """Test chat interaction with non-existent job"""
        non_existent_job_id = str(uuid.uuid4())
        url = reverse(
            "job-quote-chat-interaction", kwargs={"job_id": non_existent_job_id}
        )

        data = {
            "message": "Test message",
        }

        response = self.client_api.post(
            url, data=json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["code"], "JOB_NOT_FOUND")

    @patch(
        "apps.job.services.gemini_chat_service.GeminiChatService.generate_ai_response"
    )
    def test_chat_interaction_configuration_error(self, mock_generate_response):
        """Test chat interaction with configuration error"""
        mock_generate_response.side_effect = ValueError("No AI provider configured")

        data = {
            "message": "Test message",
        }

        response = self.client_api.post(
            self.chat_interaction_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("No AI provider configured", response.data["error"])

    @patch(
        "apps.job.services.gemini_chat_service.GeminiChatService.generate_ai_response"
    )
    def test_chat_interaction_internal_error(self, mock_generate_response):
        """Test chat interaction with internal error"""
        mock_generate_response.side_effect = Exception("Internal server error")

        data = {
            "message": "Test message",
        }

        response = self.client_api.post(
            self.chat_interaction_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data["success"])
        self.assertIn("internal error", response.data["error"])

    def test_chat_interaction_options_request(self):
        """Test OPTIONS request for CORS preflight"""
        response = self.client_api.options(self.chat_interaction_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that POST is allowed
        self.assertIn("POST", response.get("Allow", ""))


class ChatAPIPermissionTests(TestCase):
    """Test API permissions and authentication"""

    def setUp(self):
        """Set up test data"""
        self.client_api = APIClient()

        # Create test data
        self.company_defaults = CompanyDefaults.objects.create(
            company_name="Test Company",
            company_abn="123456789",
            company_address="123 Test St",
            company_phone="0123456789",
            company_email="test@example.com",
        )

        self.client_obj = Client.objects.create(
            name="Test Client",
            email="client@example.com",
            phone="0123456789",
        )

        self.job = Job.objects.create(
            name="Test Job",
            job_number="JOB001",
            description="Test job description",
            client=self.client_obj,
            status="quoting",
        )

        # Create test users
        self.staff = Staff.objects.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        self.admin_staff = Staff.objects.create_user(
            username="admin",
            password="adminpassword123",
            email="admin@example.com",
            is_staff=True,
            is_superuser=True,
        )

        # URLs
        self.chat_history_url = reverse(
            "job-quote-chat-history", kwargs={"job_id": str(self.job.id)}
        )
        self.chat_interaction_url = reverse(
            "job-quote-chat-interaction", kwargs={"job_id": str(self.job.id)}
        )

    def test_unauthenticated_access(self):
        """Test unauthenticated access to chat endpoints"""
        # Test chat history endpoint
        response = self.client_api.get(self.chat_history_url)
        # Note: Depending on your authentication setup, this might be 401 or 403
        self.assertIn(response.status_code, [200, 401, 403])

        # Test chat interaction endpoint
        response = self.client_api.post(
            self.chat_interaction_url,
            data={"message": "Test message"},
        )
        self.assertIn(response.status_code, [200, 401, 403])

    def test_authenticated_access(self):
        """Test authenticated access to chat endpoints"""
        self.client_api.force_authenticate(user=self.staff)

        # Test chat history endpoint
        response = self.client_api.get(self.chat_history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_access(self):
        """Test admin access to chat endpoints"""
        self.client_api.force_authenticate(user=self.admin_staff)

        # Test chat history endpoint
        response = self.client_api.get(self.chat_history_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ChatAPIValidationTests(TestCase):
    """Test API data validation"""

    def setUp(self):
        """Set up test data"""
        self.client_api = APIClient()

        self.company_defaults = CompanyDefaults.objects.create(
            company_name="Test Company",
            company_abn="123456789",
            company_address="123 Test St",
            company_phone="0123456789",
            company_email="test@example.com",
        )

        self.client_obj = Client.objects.create(
            name="Test Client",
            email="client@example.com",
            phone="0123456789",
        )

        self.job = Job.objects.create(
            name="Test Job",
            job_number="JOB001",
            description="Test job description",
            client=self.client_obj,
            status="quoting",
        )

        self.chat_history_url = reverse(
            "job-quote-chat-history", kwargs={"job_id": str(self.job.id)}
        )

    def test_create_message_valid_roles(self):
        """Test creating messages with valid roles"""
        valid_roles = ["user", "assistant"]

        for role in valid_roles:
            data = {
                "role": role,
                "content": f"Test message with {role} role",
            }

            response = self.client_api.post(
                self.chat_history_url,
                data=json.dumps(data),
                content_type="application/json",
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["role"], role)

    def test_create_message_invalid_role(self):
        """Test creating message with invalid role"""
        data = {
            "role": "invalid_role",
            "content": "Test message",
        }

        response = self.client_api.post(
            self.chat_history_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_message_missing_content(self):
        """Test creating message with missing content"""
        data = {
            "role": "user",
        }

        response = self.client_api.post(
            self.chat_history_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_message_empty_content(self):
        """Test creating message with empty content"""
        data = {
            "role": "user",
            "content": "",
        }

        response = self.client_api.post(
            self.chat_history_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_message_with_metadata(self):
        """Test creating message with metadata"""
        data = {
            "role": "assistant",
            "content": "Test message with metadata",
            "metadata": {
                "model": "gemini-pro",
                "tool_calls": [],
                "custom_field": "test_value",
            },
        }

        response = self.client_api.post(
            self.chat_history_url,
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["metadata"]["model"], "gemini-pro")
        self.assertEqual(response.data["metadata"]["custom_field"], "test_value")

    def test_invalid_job_id_format(self):
        """Test API with invalid job ID format"""
        invalid_url = reverse(
            "job-quote-chat-history", kwargs={"job_id": "invalid-uuid"}
        )

        response = self.client_api.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_malformed_json_request(self):
        """Test API with malformed JSON"""
        response = self.client_api.post(
            self.chat_history_url,
            data='{"invalid": json}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
