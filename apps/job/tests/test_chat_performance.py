"""
Performance tests for chat conversation flow

Tests cover:
- Response time under different loads
- Memory usage during conversation
- Concurrent chat sessions
- Large conversation history handling
- Database query optimization
"""

import threading
import time
from unittest.mock import Mock, patch

from apps.client.models import Client
from apps.job.models import Job, JobQuoteChat
from apps.job.services.gemini_chat_service import GeminiChatService
from apps.testing import BaseTestCase, BaseTransactionTestCase
from apps.workflow.enums import AIProviderTypes
from apps.workflow.models import AIProvider, CompanyDefaults, XeroPayItem


class ChatPerformanceTests(BaseTransactionTestCase):
    """Test chat performance characteristics"""

    def setUp(self):
        """Set up test data"""
        self.company_defaults = CompanyDefaults.get_instance()

        self.client = Client.objects.create(
            name="Test Client",
            email="client@example.com",
            phone="0123456789",
            xero_last_modified="2024-01-01T00:00:00Z",
        )

        # Get Ordinary Time pay item (created by migration)
        self.xero_pay_item = XeroPayItem.get_ordinary_time()

        self.job = Job.objects.create(
            name="Test Job",
            job_number="JOB001",
            description="Test job description",
            client=self.client,
            status="quoting",
            default_xero_pay_item=self.xero_pay_item,
        )

        self.ai_provider = AIProvider.objects.create(
            provider_type=AIProviderTypes.GOOGLE,
            default=True,
            api_key="test-key",
            model_name="gemini-pro",
        )

        self.service = GeminiChatService()

    def test_response_time_basic(self):
        """Test basic response time for single chat interaction"""
        with patch.object(self.service, "get_gemini_client") as mock_client:
            # Mock the Gemini client
            mock_model = Mock()
            mock_model.model_name = "gemini-pro"
            mock_client.return_value = mock_model

            mock_chat = Mock()
            mock_model.start_chat.return_value = mock_chat

            # Mock response
            mock_response = Mock()
            mock_response.text = "Test response"
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].content.parts = []
            mock_chat.send_message.return_value = mock_response

            # Measure response time
            start_time = time.time()
            result = self.service.generate_ai_response(str(self.job.id), "Test message")
            end_time = time.time()

            response_time = end_time - start_time

            # Should respond in under 2 seconds (excluding actual AI call)
            self.assertLess(response_time, 2.0)
            self.assertIsNotNone(result)

    def test_response_time_with_history(self):
        """Test response time with conversation history"""
        # Create conversation history
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            JobQuoteChat.objects.create(
                job=self.job,
                message_id=f"msg-{i}",
                role=role,
                content=f"Message {i}",
            )

        with patch.object(self.service, "get_gemini_client") as mock_client:
            mock_model = Mock()
            mock_model.model_name = "gemini-pro"
            mock_client.return_value = mock_model

            mock_chat = Mock()
            mock_model.start_chat.return_value = mock_chat

            mock_response = Mock()
            mock_response.text = "Response with history"
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].content.parts = []
            mock_chat.send_message.return_value = mock_response

            start_time = time.time()
            result = self.service.generate_ai_response(str(self.job.id), "New message")
            end_time = time.time()

            response_time = end_time - start_time

            # Should still respond reasonably fast with history
            self.assertLess(response_time, 3.0)
            self.assertIsNotNone(result)

    def test_concurrent_chat_sessions(self):
        """Test handling of concurrent chat sessions"""
        # Create multiple jobs
        jobs = []
        for i in range(5):
            job = Job.objects.create(
                name=f"Concurrent Job {i}",
                job_number=f"CONCURRENT{i:03d}",
                description=f"Concurrent test job {i}",
                client=self.client,
                status="quoting",
                default_xero_pay_item=self.xero_pay_item,
            )
            jobs.append(job)

        results = []
        errors = []

        def chat_interaction(job_id, message):
            try:
                with patch.object(self.service, "get_gemini_client") as mock_client:
                    mock_model = Mock()
                    mock_model.model_name = "gemini-pro"
                    mock_client.return_value = mock_model

                    mock_chat = Mock()
                    mock_model.start_chat.return_value = mock_chat

                    mock_response = Mock()
                    mock_response.text = f"Response for {job_id}"
                    mock_response.candidates = [Mock()]
                    mock_response.candidates[0].content.parts = []
                    mock_chat.send_message.return_value = mock_response

                    service = GeminiChatService()
                    result = service.generate_ai_response(job_id, message)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Start concurrent threads
        threads = []
        for i, job in enumerate(jobs):
            thread = threading.Thread(
                target=chat_interaction, args=(str(job.id), f"Concurrent message {i}")
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)

        # Verify all results are unique
        result_ids = [r.id for r in results]
        self.assertEqual(len(result_ids), len(set(result_ids)))

    def test_memory_usage_conversation(self):
        """Test memory usage during conversation"""
        import tracemalloc

        tracemalloc.start()

        # Simulate a conversation
        with patch.object(self.service, "get_gemini_client") as mock_client:
            mock_model = Mock()
            mock_model.model_name = "gemini-pro"
            mock_client.return_value = mock_model

            mock_chat = Mock()
            mock_model.start_chat.return_value = mock_chat

            mock_response = Mock()
            mock_response.text = "Test response"
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].content.parts = []
            mock_chat.send_message.return_value = mock_response

            # Generate multiple responses
            for i in range(10):
                result = self.service.generate_ai_response(
                    str(self.job.id), f"Message {i}"
                )
                self.assertIsNotNone(result)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory usage should be reasonable (less than 100MB)
        self.assertLess(peak, 100 * 1024 * 1024)  # 100MB

    def test_large_conversation_history(self):
        """Test handling of large conversation history"""
        # Create large conversation history
        batch_size = 100
        for batch in range(5):  # 500 messages total
            messages = []
            for i in range(batch_size):
                msg_index = batch * batch_size + i
                role = "user" if msg_index % 2 == 0 else "assistant"
                messages.append(
                    JobQuoteChat(
                        job=self.job,
                        message_id=f"large-msg-{msg_index}",
                        role=role,
                        content=f"Large conversation message {msg_index}",
                    )
                )

            JobQuoteChat.objects.bulk_create(messages)

        # Test response time with large history
        with patch.object(self.service, "get_gemini_client") as mock_client:
            mock_model = Mock()
            mock_model.model_name = "gemini-pro"
            mock_client.return_value = mock_model

            mock_chat = Mock()
            mock_model.start_chat.return_value = mock_chat

            mock_response = Mock()
            mock_response.text = "Response with large history"
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].content.parts = []
            mock_chat.send_message.return_value = mock_response

            start_time = time.time()
            result = self.service.generate_ai_response(str(self.job.id), "New message")
            end_time = time.time()

            response_time = end_time - start_time

            # Should handle large history efficiently
            self.assertLess(response_time, 5.0)
            self.assertIsNotNone(result)

    def test_database_query_optimization(self):
        """Test database query optimization"""
        # Create conversation history
        for i in range(50):
            role = "user" if i % 2 == 0 else "assistant"
            JobQuoteChat.objects.create(
                job=self.job,
                message_id=f"opt-msg-{i}",
                role=role,
                content=f"Optimization test message {i}",
            )

        # Monitor database queries
        with patch.object(self.service, "get_gemini_client") as mock_client:
            mock_model = Mock()
            mock_model.model_name = "gemini-pro"
            mock_client.return_value = mock_model

            mock_chat = Mock()
            mock_model.start_chat.return_value = mock_chat

            mock_response = Mock()
            mock_response.text = "Optimized response"
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].content.parts = []
            mock_chat.send_message.return_value = mock_response

            with self.assertNumQueries(5):  # Should use minimal queries
                result = self.service.generate_ai_response(
                    str(self.job.id), "Test message"
                )
                self.assertIsNotNone(result)

    def test_tool_execution_performance(self):
        """Test tool execution performance"""
        with patch.object(self.service, "get_gemini_client") as mock_client:
            mock_model = Mock()
            mock_model.model_name = "gemini-pro"
            mock_client.return_value = mock_model

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

            # Mock final response
            mock_final_response = Mock()
            mock_final_response.text = "Tool execution complete"
            mock_final_response.candidates = [Mock()]
            mock_final_response.candidates[0].content.parts = []

            mock_chat.send_message.side_effect = [
                mock_initial_response,
                mock_final_response,
            ]

            # Mock tool execution
            with patch.object(
                self.service, "_execute_mcp_tool", return_value="Tool result"
            ):
                start_time = time.time()
                result = self.service.generate_ai_response(
                    str(self.job.id), "Search products"
                )
                end_time = time.time()

                execution_time = end_time - start_time

                # Tool execution should be fast
                self.assertLess(execution_time, 3.0)
                self.assertIsNotNone(result)

    def test_concurrent_database_access(self):
        """Test concurrent database access performance"""
        jobs = []
        for i in range(3):
            job = Job.objects.create(
                name=f"DB Test Job {i}",
                job_number=f"DB{i:03d}",
                description=f"Database test job {i}",
                client=self.client,
                status="quoting",
                default_xero_pay_item=self.xero_pay_item,
            )
            jobs.append(job)

        def create_messages(job):
            for i in range(20):
                role = "user" if i % 2 == 0 else "assistant"
                JobQuoteChat.objects.create(
                    job=job,
                    message_id=f"concurrent-{job.id}-{i}",
                    role=role,
                    content=f"Concurrent message {i}",
                )

        # Create messages concurrently
        threads = []
        for job in jobs:
            thread = threading.Thread(target=create_messages, args=(job,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all messages were created
        total_messages = JobQuoteChat.objects.filter(job__in=jobs).count()
        self.assertEqual(total_messages, 60)  # 3 jobs * 20 messages each

    def test_streaming_response_simulation(self):
        """Test streaming response simulation performance"""
        # Simulate streaming by creating incremental responses
        large_response = "This is a very long response that would be streamed. " * 100

        with patch.object(self.service, "get_gemini_client") as mock_client:
            mock_model = Mock()
            mock_model.model_name = "gemini-pro"
            mock_client.return_value = mock_model

            mock_chat = Mock()
            mock_model.start_chat.return_value = mock_chat

            mock_response = Mock()
            mock_response.text = large_response
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].content.parts = []
            mock_chat.send_message.return_value = mock_response

            start_time = time.time()
            result = self.service.generate_ai_response(
                str(self.job.id), "Generate long response"
            )
            end_time = time.time()

            response_time = end_time - start_time

            # Should handle large responses efficiently
            self.assertLess(response_time, 2.0)
            self.assertEqual(len(result.content), len(large_response))

    def test_metadata_storage_performance(self):
        """Test metadata storage performance"""
        # Test with large metadata
        large_metadata = {
            "model": "gemini-pro",
            "tool_calls": [
                {
                    "name": f"tool_{i}",
                    "arguments": {"param": f"value_{i}"},
                    "result": f"Large result data {i}" * 50,
                }
                for i in range(10)
            ],
            "system_prompt": "System prompt " * 100,
            "chat_history": [
                {"role": "user", "content": f"History message {i}"} for i in range(50)
            ],
        }

        start_time = time.time()

        message = JobQuoteChat.objects.create(
            job=self.job,
            message_id="metadata-perf-test",
            role="assistant",
            content="Response with large metadata",
            metadata=large_metadata,
        )

        end_time = time.time()
        creation_time = end_time - start_time

        # Metadata storage should be fast
        self.assertLess(creation_time, 1.0)

        # Verify metadata was stored correctly
        retrieved_message = JobQuoteChat.objects.get(id=message.id)
        self.assertEqual(len(retrieved_message.metadata["tool_calls"]), 10)
        self.assertEqual(len(retrieved_message.metadata["chat_history"]), 50)


class ChatLoadTests(BaseTestCase):
    """Test chat system under load"""

    def setUp(self):
        """Set up test data"""
        self.company_defaults = CompanyDefaults.get_instance()

        self.client = Client.objects.create(
            name="Test Client",
            email="client@example.com",
            phone="0123456789",
            xero_last_modified="2024-01-01T00:00:00Z",
        )

        # Get Ordinary Time pay item (created by migration)
        self.xero_pay_item = XeroPayItem.get_ordinary_time()

    def test_multiple_jobs_chat_history(self):
        """Test performance with multiple jobs having chat history"""
        # Create multiple jobs with chat history
        jobs = []
        for i in range(10):
            job = Job.objects.create(
                name=f"Load Test Job {i}",
                job_number=f"LOAD{i:03d}",
                description=f"Load test job {i}",
                client=self.client,
                status="quoting",
                default_xero_pay_item=self.xero_pay_item,
            )
            jobs.append(job)

            # Add chat history to each job
            for j in range(10):
                role = "user" if j % 2 == 0 else "assistant"
                JobQuoteChat.objects.create(
                    job=job,
                    message_id=f"load-{i}-{j}",
                    role=role,
                    content=f"Load test message {j} for job {i}",
                )

        # Test querying all chat messages
        start_time = time.time()
        all_messages = JobQuoteChat.objects.all()
        message_count = all_messages.count()
        end_time = time.time()

        query_time = end_time - start_time

        # Should handle 100 messages efficiently
        self.assertEqual(message_count, 100)
        self.assertLess(query_time, 1.0)

    def test_chat_history_pagination(self):
        """Test chat history pagination performance"""
        job = Job.objects.create(
            name="Pagination Test Job",
            job_number="PAGINATION001",
            description="Pagination test job",
            client=self.client,
            status="quoting",
            default_xero_pay_item=self.xero_pay_item,
        )

        # Create many messages
        messages = []
        for i in range(200):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(
                JobQuoteChat(
                    job=job,
                    message_id=f"page-msg-{i}",
                    role=role,
                    content=f"Pagination message {i}",
                )
            )

        JobQuoteChat.objects.bulk_create(messages)

        # Test pagination queries
        start_time = time.time()

        # Get first page
        page1 = JobQuoteChat.objects.filter(job=job).order_by("timestamp")[:20]
        list(page1)  # Force evaluation

        # Get middle page
        page_middle = JobQuoteChat.objects.filter(job=job).order_by("timestamp")[80:100]
        list(page_middle)  # Force evaluation

        # Get last page
        page_last = JobQuoteChat.objects.filter(job=job).order_by("timestamp")[180:200]
        list(page_last)  # Force evaluation

        end_time = time.time()
        pagination_time = end_time - start_time

        # Pagination should be efficient
        self.assertLess(pagination_time, 1.0)

    def test_search_performance(self):
        """Test search performance across chat messages"""
        job = Job.objects.create(
            name="Search Test Job",
            job_number="SEARCH001",
            description="Search test job",
            client=self.client,
            status="quoting",
            default_xero_pay_item=self.xero_pay_item,
        )

        # Create messages with searchable content
        search_terms = ["steel", "aluminum", "welding", "cutting", "pricing"]
        for i in range(100):
            term = search_terms[i % len(search_terms)]
            JobQuoteChat.objects.create(
                job=job,
                message_id=f"search-msg-{i}",
                role="user" if i % 2 == 0 else "assistant",
                content=f"This message contains {term} information and other details.",
            )

        # Test search performance
        start_time = time.time()

        # Search for each term
        for term in search_terms:
            results = JobQuoteChat.objects.filter(job=job, content__icontains=term)
            list(results)  # Force evaluation

        end_time = time.time()
        search_time = end_time - start_time

        # Search should be efficient
        self.assertLess(search_time, 2.0)
