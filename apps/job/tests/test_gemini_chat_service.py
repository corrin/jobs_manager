"""
Comprehensive unit tests for GeminiChatService

Tests cover:
- Service initialization and configuration
- AI response generation
- Tool integration and execution
- Error handling and edge cases
- Message persistence and metadata
"""

import json
import uuid
from unittest.mock import Mock, patch, MagicMock
import pytest
from django.test import TestCase, TransactionTestCase
from django.db import transaction

from apps.job.models import Job, JobQuoteChat
from apps.job.services.gemini_chat_service import GeminiChatService
from apps.workflow.models import AIProvider, CompanyDefaults
from apps.workflow.enums import AIProviderTypes
from apps.client.models import Client
from apps.accounts.models import Staff


class GeminiChatServiceConfigurationTests(TestCase):
    """Test service configuration and initialization"""
    
    def setUp(self):
        """Set up test data"""
        self.company_defaults = CompanyDefaults.objects.create(
            company_name="Test Company",
            company_abn="123456789",
            company_address="123 Test St",
            company_phone="0123456789",
            company_email="test@example.com",
        )
        
        self.client = Client.objects.create(
            name="Test Client",
            email="client@example.com",
            phone="0123456789",
        )
        
        self.job = Job.objects.create(
            name="Test Job",
            job_number="JOB001",
            description="Test job description",
            client=self.client,
            status="quoting",
        )
        
        self.service = GeminiChatService()
    
    def test_service_initialization(self):
        """Test service initializes with required tools"""
        self.assertIsNotNone(self.service.quoting_tool)
        self.assertIsNotNone(self.service.query_tool)
    
    def test_get_gemini_client_no_provider(self):
        """Test client creation fails when no AI provider configured"""
        with self.assertRaises(ValueError) as context:
            self.service.get_gemini_client()
        
        self.assertIn("No default Gemini AI provider configured", str(context.exception))
    
    def test_get_gemini_client_no_api_key(self):
        """Test client creation fails when provider has no API key"""
        AIProvider.objects.create(
            provider_type=AIProviderTypes.GOOGLE,
            default=True,
            model_name="gemini-pro",
            # No api_key set
        )
        
        with self.assertRaises(ValueError) as context:
            self.service.get_gemini_client()
        
        self.assertIn("missing an API key", str(context.exception))
    
    def test_get_gemini_client_no_model_name(self):
        """Test client creation fails when provider has no model name"""
        AIProvider.objects.create(
            provider_type=AIProviderTypes.GOOGLE,
            default=True,
            api_key="test-key",
            # No model_name set
        )
        
        with self.assertRaises(ValueError) as context:
            self.service.get_gemini_client()
        
        self.assertIn("missing a model name", str(context.exception))
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_get_gemini_client_success(self, mock_model, mock_configure):
        """Test successful client creation"""
        AIProvider.objects.create(
            provider_type=AIProviderTypes.GOOGLE,
            default=True,
            api_key="test-key",
            model_name="gemini-pro",
        )
        
        mock_model_instance = Mock()
        mock_model.return_value = mock_model_instance
        
        client = self.service.get_gemini_client()
        
        mock_configure.assert_called_once_with(api_key="test-key")
        mock_model.assert_called_once_with(
            model_name="gemini-pro",
            tools=self.service._get_mcp_tools(),
        )
        self.assertEqual(client, mock_model_instance)
    
    def test_system_prompt_generation(self):
        """Test system prompt includes job context"""
        prompt = self.service._get_system_prompt(self.job)
        
        self.assertIn("Morris Sheetmetal Works", prompt)
        self.assertIn(self.job.name, prompt)
        self.assertIn(self.job.job_number, prompt)
        self.assertIn(self.client.name, prompt)
        self.assertIn(self.job.description, prompt)
    
    def test_mcp_tools_definition(self):
        """Test MCP tools are properly defined"""
        tools = self.service._get_mcp_tools()
        
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)
        
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "search_products",
            "get_pricing_for_material", 
            "create_quote_estimate",
            "get_supplier_status",
            "compare_suppliers",
        ]
        
        for expected_tool in expected_tools:
            self.assertIn(expected_tool, tool_names)
    
    def test_role_conversion(self):
        """Test database role to Gemini role conversion"""
        self.assertEqual(self.service._to_gemini_role("user"), "user")
        self.assertEqual(self.service._to_gemini_role("assistant"), "model")
        self.assertEqual(self.service._to_gemini_role("system"), "user")


class GeminiChatServiceToolExecutionTests(TestCase):
    """Test MCP tool execution"""
    
    def setUp(self):
        self.service = GeminiChatService()
    
    @patch('apps.job.services.gemini_chat_service.GeminiChatService.quoting_tool')
    def test_execute_search_products_tool(self, mock_quoting_tool):
        """Test search_products tool execution"""
        mock_quoting_tool.search_products.return_value = "Found 5 products"
        
        result = self.service._execute_mcp_tool(
            "search_products", 
            {"query": "steel angle", "supplier_name": "Test Supplier"}
        )
        
        mock_quoting_tool.search_products.assert_called_once_with(
            query="steel angle", 
            supplier_name="Test Supplier"
        )
        self.assertEqual(result, "Found 5 products")
    
    @patch('apps.job.services.gemini_chat_service.GeminiChatService.quoting_tool')
    def test_execute_pricing_tool(self, mock_quoting_tool):
        """Test get_pricing_for_material tool execution"""
        mock_quoting_tool.get_pricing_for_material.return_value = "Steel: $5.50/kg"
        
        result = self.service._execute_mcp_tool(
            "get_pricing_for_material",
            {"material_type": "steel", "dimensions": "4x8"}
        )
        
        mock_quoting_tool.get_pricing_for_material.assert_called_once_with(
            material_type="steel", 
            dimensions="4x8"
        )
        self.assertEqual(result, "Steel: $5.50/kg")
    
    def test_execute_unknown_tool(self):
        """Test execution of unknown tool"""
        result = self.service._execute_mcp_tool("unknown_tool", {})
        self.assertEqual(result, "Unknown tool: unknown_tool")
    
    @patch('apps.job.services.gemini_chat_service.GeminiChatService.quoting_tool')
    def test_execute_tool_with_exception(self, mock_quoting_tool):
        """Test tool execution with exception"""
        mock_quoting_tool.search_products.side_effect = Exception("Tool error")
        
        result = self.service._execute_mcp_tool("search_products", {"query": "test"})
        
        self.assertIn("Error executing tool", result)
        self.assertIn("Tool error", result)


class GeminiChatServiceResponseGenerationTests(TransactionTestCase):
    """Test AI response generation with database transactions"""
    
    def setUp(self):
        """Set up test data"""
        self.company_defaults = CompanyDefaults.objects.create(
            company_name="Test Company",
            company_abn="123456789",
            company_address="123 Test St",
            company_phone="0123456789",
            company_email="test@example.com",
        )
        
        self.client = Client.objects.create(
            name="Test Client",
            email="client@example.com",
            phone="0123456789",
        )
        
        self.job = Job.objects.create(
            name="Test Job",
            job_number="JOB001",
            description="Test job description",
            client=self.client,
            status="quoting",
        )
        
        self.ai_provider = AIProvider.objects.create(
            provider_type=AIProviderTypes.GOOGLE,
            default=True,
            api_key="test-key",
            model_name="gemini-pro",
        )
        
        self.service = GeminiChatService()
    
    def test_job_not_found(self):
        """Test response generation with non-existent job"""
        non_existent_job_id = str(uuid.uuid4())
        
        with self.assertRaises(Job.DoesNotExist):
            self.service.generate_ai_response(non_existent_job_id, "Test message")
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_generate_response_simple(self, mock_model_class, mock_configure):
        """Test simple response generation without tool calls"""
        # Mock the model and chat
        mock_model = Mock()
        mock_model.model_name = "gemini-pro"
        mock_model_class.return_value = mock_model
        
        mock_chat = Mock()
        mock_model.start_chat.return_value = mock_chat
        
        # Mock response without tool calls
        mock_response = Mock()
        mock_response.text = "This is a test response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = []
        mock_chat.send_message.return_value = mock_response
        
        result = self.service.generate_ai_response(str(self.job.id), "Test message")
        
        self.assertIsInstance(result, JobQuoteChat)
        self.assertEqual(result.job, self.job)
        self.assertEqual(result.role, "assistant")
        self.assertEqual(result.content, "This is a test response")
        self.assertIn("model", result.metadata)
        self.assertIn("user_message", result.metadata)
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_generate_response_with_tool_calls(self, mock_model_class, mock_configure):
        """Test response generation with tool calls"""
        # Mock the model and chat
        mock_model = Mock()
        mock_model.model_name = "gemini-pro"
        mock_model_class.return_value = mock_model
        
        mock_chat = Mock()
        mock_model.start_chat.return_value = mock_chat
        
        # Mock initial response with tool call
        mock_function_call = Mock()
        mock_function_call.name = "search_products"
        mock_function_call.args = {"query": "steel"}
        
        mock_part_with_tool = Mock()
        mock_part_with_tool.function_call = mock_function_call
        
        mock_initial_response = Mock()
        mock_initial_response.candidates = [Mock()]
        mock_initial_response.candidates[0].content.parts = [mock_part_with_tool]
        
        # Mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.text = "Based on the search results, here are some steel options..."
        mock_final_response.candidates = [Mock()]
        mock_final_response.candidates[0].content.parts = []
        
        mock_chat.send_message.side_effect = [mock_initial_response, mock_final_response]
        
        # Mock tool execution
        with patch.object(self.service, '_execute_mcp_tool', return_value="Tool result"):
            result = self.service.generate_ai_response(str(self.job.id), "Find steel products")
            
            self.assertIsInstance(result, JobQuoteChat)
            self.assertEqual(result.role, "assistant")
            self.assertIn("tool_calls", result.metadata)
            self.assertEqual(len(result.metadata["tool_calls"]), 1)
            self.assertEqual(result.metadata["tool_calls"][0]["name"], "search_products")
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_generate_response_with_history(self, mock_model_class, mock_configure):
        """Test response generation includes conversation history"""
        # Create some existing chat messages
        JobQuoteChat.objects.create(
            job=self.job,
            message_id="user-1",
            role="user",
            content="Previous user message",
        )
        JobQuoteChat.objects.create(
            job=self.job,
            message_id="assistant-1",
            role="assistant",
            content="Previous assistant response",
        )
        
        # Mock the model and chat
        mock_model = Mock()
        mock_model.model_name = "gemini-pro"
        mock_model_class.return_value = mock_model
        
        mock_chat = Mock()
        mock_model.start_chat.return_value = mock_chat
        
        # Mock response
        mock_response = Mock()
        mock_response.text = "Response with history context"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = []
        mock_chat.send_message.return_value = mock_response
        
        result = self.service.generate_ai_response(str(self.job.id), "New message")
        
        # Verify chat was started with history
        mock_model.start_chat.assert_called_once()
        call_args = mock_model.start_chat.call_args[1]
        self.assertIn('history', call_args)
        self.assertEqual(len(call_args['history']), 2)
        
        # Verify response includes history in metadata
        self.assertIn("chat_history", result.metadata)
        self.assertEqual(len(result.metadata["chat_history"]), 2)
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_generate_response_error_handling(self, mock_model_class, mock_configure):
        """Test error handling in response generation"""
        # Mock the model to raise an exception
        mock_model_class.side_effect = Exception("API Error")
        
        result = self.service.generate_ai_response(str(self.job.id), "Test message")
        
        self.assertIsInstance(result, JobQuoteChat)
        self.assertEqual(result.role, "assistant")
        self.assertIn("error", result.content)
        self.assertIn("API Error", result.content)
        self.assertTrue(result.metadata.get("error", False))


class GeminiChatServiceIntegrationTests(TestCase):
    """Integration tests for the complete chat flow"""
    
    def setUp(self):
        """Set up test data"""
        self.company_defaults = CompanyDefaults.objects.create(
            company_name="Test Company",
            company_abn="123456789",
            company_address="123 Test St",
            company_phone="0123456789",
            company_email="test@example.com",
        )
        
        self.client = Client.objects.create(
            name="Test Client",
            email="client@example.com",
            phone="0123456789",
        )
        
        self.job = Job.objects.create(
            name="Test Job",
            job_number="JOB001",
            description="Test job description",
            client=self.client,
            status="quoting",
        )
        
        self.ai_provider = AIProvider.objects.create(
            provider_type=AIProviderTypes.GOOGLE,
            default=True,
            api_key="test-key",
            model_name="gemini-pro",
        )
    
    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_complete_chat_flow(self, mock_model_class, mock_configure):
        """Test complete chat flow from user message to saved response"""
        service = GeminiChatService()
        
        # Mock the model and chat
        mock_model = Mock()
        mock_model.model_name = "gemini-pro"
        mock_model_class.return_value = mock_model
        
        mock_chat = Mock()
        mock_model.start_chat.return_value = mock_chat
        
        # Mock response
        mock_response = Mock()
        mock_response.text = "Complete chat flow response"
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = []
        mock_chat.send_message.return_value = mock_response
        
        # Execute the flow
        result = service.generate_ai_response(str(self.job.id), "Test complete flow")
        
        # Verify response
        self.assertIsInstance(result, JobQuoteChat)
        self.assertEqual(result.job, self.job)
        self.assertEqual(result.role, "assistant")
        self.assertEqual(result.content, "Complete chat flow response")
        
        # Verify message was saved to database
        saved_message = JobQuoteChat.objects.get(id=result.id)
        self.assertEqual(saved_message.content, "Complete chat flow response")
        self.assertIn("model", saved_message.metadata)
        self.assertIn("user_message", saved_message.metadata)
        self.assertIn("tool_definitions", saved_message.metadata)
    
    def test_conversation_persistence(self):
        """Test that conversation history is properly maintained"""
        # Create a sequence of messages
        messages = [
            ("user", "Hello"),
            ("assistant", "Hi there!"),
            ("user", "What can you help with?"),
            ("assistant", "I can help with quoting and materials"),
        ]
        
        for role, content in messages:
            JobQuoteChat.objects.create(
                job=self.job,
                message_id=f"{role}-{uuid.uuid4()}",
                role=role,
                content=content,
            )
        
        # Verify messages are retrievable in order
        history = JobQuoteChat.objects.filter(job=self.job).order_by("timestamp")
        self.assertEqual(history.count(), 4)
        
        for i, msg in enumerate(history):
            self.assertEqual(msg.role, messages[i][0])
            self.assertEqual(msg.content, messages[i][1])