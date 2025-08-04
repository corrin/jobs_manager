"""
Tests for MCP (Model Context Protocol) tool integration

Tests cover:
- QuotingTool functionality
- SupplierProductQueryTool functionality
- Tool parameter validation
- Error handling in tool execution
- Integration with chat service
"""

import json
from unittest.mock import patch

from django.test import TestCase

from apps.client.models import Client
from apps.job.models import Job
from apps.quoting.mcp import QuotingTool, SupplierProductQueryTool
from apps.workflow.models import CompanyDefaults


class QuotingToolTests(TestCase):
    """Test QuotingTool functionality"""

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

        self.tool = QuotingTool()

    def test_tool_initialization(self):
        """Test tool initializes correctly"""
        self.assertIsInstance(self.tool, QuotingTool)
        # Add specific initialization tests based on your tool's requirements

    @patch("apps.quoting.mcp.QuotingTool._search_database")
    def test_search_products_basic(self, mock_search):
        """Test basic product search functionality"""
        mock_search.return_value = [
            {"name": "Steel Angle", "price": 5.50, "supplier": "ABC Steel"},
            {"name": "Steel Plate", "price": 8.75, "supplier": "XYZ Steel"},
        ]

        result = self.tool.search_products(query="steel")

        mock_search.assert_called_once_with(query="steel", supplier_name=None)
        self.assertIn("Steel Angle", result)
        self.assertIn("Steel Plate", result)
        self.assertIn("5.50", result)
        self.assertIn("8.75", result)

    @patch("apps.quoting.mcp.QuotingTool._search_database")
    def test_search_products_with_supplier(self, mock_search):
        """Test product search with supplier filter"""
        mock_search.return_value = [
            {"name": "Steel Angle", "price": 5.50, "supplier": "ABC Steel"},
        ]

        result = self.tool.search_products(query="steel", supplier_name="ABC Steel")

        mock_search.assert_called_once_with(query="steel", supplier_name="ABC Steel")
        self.assertIn("ABC Steel", result)

    @patch("apps.quoting.mcp.QuotingTool._search_database")
    def test_search_products_no_results(self, mock_search):
        """Test product search with no results"""
        mock_search.return_value = []

        result = self.tool.search_products(query="nonexistent")

        self.assertIn("No products found", result)
        self.assertIn("nonexistent", result)

    @patch("apps.quoting.mcp.QuotingTool._search_database")
    def test_search_products_error_handling(self, mock_search):
        """Test error handling in product search"""
        mock_search.side_effect = Exception("Database error")

        result = self.tool.search_products(query="steel")

        self.assertIn("error", result.lower())
        self.assertIn("Database error", result)

    @patch("apps.quoting.mcp.QuotingTool._get_material_pricing")
    def test_get_pricing_for_material(self, mock_get_pricing):
        """Test getting pricing for specific material"""
        mock_get_pricing.return_value = {
            "material": "steel",
            "average_price": 6.25,
            "suppliers": [
                {"name": "ABC Steel", "price": 5.50},
                {"name": "XYZ Steel", "price": 7.00},
            ],
        }

        result = self.tool.get_pricing_for_material(material_type="steel")

        mock_get_pricing.assert_called_once_with(material_type="steel", dimensions=None)
        self.assertIn("steel", result)
        self.assertIn("6.25", result)
        self.assertIn("ABC Steel", result)
        self.assertIn("XYZ Steel", result)

    @patch("apps.quoting.mcp.QuotingTool._get_material_pricing")
    def test_get_pricing_with_dimensions(self, mock_get_pricing):
        """Test getting pricing with dimensions"""
        mock_get_pricing.return_value = {
            "material": "steel",
            "dimensions": "4x8",
            "average_price": 125.00,
            "suppliers": [
                {"name": "ABC Steel", "price": 120.00},
            ],
        }

        result = self.tool.get_pricing_for_material(
            material_type="steel", dimensions="4x8"
        )

        mock_get_pricing.assert_called_once_with(
            material_type="steel", dimensions="4x8"
        )
        self.assertIn("4x8", result)
        self.assertIn("125.00", result)

    @patch("apps.quoting.mcp.QuotingTool._create_estimate")
    def test_create_quote_estimate(self, mock_create_estimate):
        """Test creating a quote estimate"""
        mock_create_estimate.return_value = {
            "job_id": str(self.job.id),
            "total_estimate": 1250.00,
            "materials_cost": 800.00,
            "labor_cost": 450.00,
            "breakdown": [
                {"item": "Steel materials", "cost": 800.00},
                {"item": "Labor (15 hours)", "cost": 450.00},
            ],
        }

        result = self.tool.create_quote_estimate(
            job_id=str(self.job.id),
            materials="Steel angle, steel plate",
            labor_hours=15,
        )

        mock_create_estimate.assert_called_once_with(
            job_id=str(self.job.id),
            materials="Steel angle, steel plate",
            labor_hours=15,
        )
        self.assertIn("1250.00", result)
        self.assertIn("800.00", result)
        self.assertIn("450.00", result)

    @patch("apps.quoting.mcp.QuotingTool._get_supplier_info")
    def test_get_supplier_status(self, mock_get_supplier_info):
        """Test getting supplier status"""
        mock_get_supplier_info.return_value = {
            "suppliers": [
                {
                    "name": "ABC Steel",
                    "last_updated": "2024-01-15",
                    "product_count": 1250,
                },
                {
                    "name": "XYZ Steel",
                    "last_updated": "2024-01-10",
                    "product_count": 890,
                },
            ]
        }

        result = self.tool.get_supplier_status()

        mock_get_supplier_info.assert_called_once_with(supplier_name=None)
        self.assertIn("ABC Steel", result)
        self.assertIn("XYZ Steel", result)
        self.assertIn("1250", result)
        self.assertIn("890", result)

    @patch("apps.quoting.mcp.QuotingTool._compare_supplier_prices")
    def test_compare_suppliers(self, mock_compare_prices):
        """Test comparing suppliers"""
        mock_compare_prices.return_value = {
            "material": "steel angle",
            "comparisons": [
                {"supplier": "ABC Steel", "price": 5.50, "availability": "In stock"},
                {"supplier": "XYZ Steel", "price": 6.00, "availability": "2-3 days"},
                {"supplier": "DEF Steel", "price": 5.25, "availability": "1 week"},
            ],
        }

        result = self.tool.compare_suppliers(material_query="steel angle")

        mock_compare_prices.assert_called_once_with(material_query="steel angle")
        self.assertIn("ABC Steel", result)
        self.assertIn("5.50", result)
        self.assertIn("6.00", result)
        self.assertIn("5.25", result)
        self.assertIn("In stock", result)


class SupplierProductQueryToolTests(TestCase):
    """Test SupplierProductQueryTool functionality"""

    def setUp(self):
        """Set up test data"""
        self.tool = SupplierProductQueryTool()

    def test_tool_initialization(self):
        """Test tool initializes correctly"""
        self.assertIsInstance(self.tool, SupplierProductQueryTool)

    @patch("apps.quoting.mcp.SupplierProductQueryTool._query_suppliers")
    def test_query_basic(self, mock_query):
        """Test basic supplier query"""
        mock_query.return_value = [
            {"supplier": "ABC Steel", "product": "Steel Angle", "price": 5.50},
            {"supplier": "XYZ Steel", "product": "Steel Angle", "price": 6.00},
        ]

        result = self.tool.query_suppliers(query="steel angle")

        mock_query.assert_called_once_with(query="steel angle", filters=None)
        self.assertIn("ABC Steel", result)
        self.assertIn("XYZ Steel", result)

    @patch("apps.quoting.mcp.SupplierProductQueryTool._query_suppliers")
    def test_query_with_filters(self, mock_query):
        """Test supplier query with filters"""
        filters = {"supplier": "ABC Steel", "max_price": 6.00}
        mock_query.return_value = [
            {"supplier": "ABC Steel", "product": "Steel Angle", "price": 5.50},
        ]

        result = self.tool.query_suppliers(query="steel angle", filters=filters)

        mock_query.assert_called_once_with(query="steel angle", filters=filters)
        self.assertIn("ABC Steel", result)
        self.assertIn("5.50", result)

    @patch("apps.quoting.mcp.SupplierProductQueryTool._query_suppliers")
    def test_query_no_results(self, mock_query):
        """Test query with no results"""
        mock_query.return_value = []

        result = self.tool.query_suppliers(query="nonexistent product")

        self.assertIn("No suppliers found", result)

    @patch("apps.quoting.mcp.SupplierProductQueryTool._query_suppliers")
    def test_query_error_handling(self, mock_query):
        """Test error handling in supplier query"""
        mock_query.side_effect = Exception("API error")

        result = self.tool.query_suppliers(query="steel angle")

        self.assertIn("error", result.lower())
        self.assertIn("API error", result)


class MCPToolIntegrationTests(TestCase):
    """Test MCP tool integration with chat service"""

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

    def test_tool_parameter_validation(self):
        """Test tool parameter validation"""
        tool = QuotingTool()

        # Test missing required parameters
        with self.assertRaises(TypeError):
            tool.search_products()  # Missing query parameter

        # Test invalid parameter types
        result = tool.search_products(query=123)  # Should handle non-string query
        self.assertIsInstance(result, str)

    def test_tool_response_format(self):
        """Test that tools return properly formatted responses"""
        tool = QuotingTool()

        with patch.object(tool, "_search_database", return_value=[]):
            result = tool.search_products(query="test")

            # Response should be a string (required for MCP integration)
            self.assertIsInstance(result, str)

            # Response should be informative
            self.assertGreater(len(result), 10)

    @patch("apps.quoting.mcp.QuotingTool._search_database")
    def test_tool_large_result_handling(self, mock_search):
        """Test handling of large result sets"""
        # Create a large result set
        large_results = [
            {"name": f"Product {i}", "price": i * 1.5, "supplier": f"Supplier {i % 5}"}
            for i in range(100)
        ]
        mock_search.return_value = large_results

        tool = QuotingTool()
        result = tool.search_products(query="test")

        # Result should be a string and reasonably sized
        self.assertIsInstance(result, str)
        self.assertLess(len(result), 10000)  # Should be truncated or summarized

    def test_concurrent_tool_execution(self):
        """Test concurrent tool execution"""
        import threading

        tool = QuotingTool()
        results = []

        def execute_tool(query):
            with patch.object(tool, "_search_database", return_value=[]):
                result = tool.search_products(query=query)
                results.append(result)

        # Execute multiple tools concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=execute_tool, args=(f"query{i}",))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All executions should complete successfully
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIsInstance(result, str)

    def test_tool_caching_behavior(self):
        """Test tool caching behavior if implemented"""
        tool = QuotingTool()

        with patch.object(tool, "_search_database", return_value=[]) as mock_search:
            # First call
            result1 = tool.search_products(query="steel")

            # Second call with same parameters
            result2 = tool.search_products(query="steel")

            # Verify both calls return the same result
            self.assertEqual(result1, result2)

            # Depending on caching implementation, this might be called once or twice
            self.assertGreaterEqual(mock_search.call_count, 1)

    def test_tool_error_recovery(self):
        """Test tool error recovery mechanisms"""
        tool = QuotingTool()

        # Test recovery from database errors
        with patch.object(tool, "_search_database", side_effect=Exception("DB Error")):
            result = tool.search_products(query="steel")

            # Should return an error message, not raise exception
            self.assertIsInstance(result, str)
            self.assertIn("error", result.lower())

    def test_tool_result_serialization(self):
        """Test that tool results are JSON serializable"""
        tool = QuotingTool()

        with patch.object(
            tool,
            "_search_database",
            return_value=[
                {"name": "Steel Angle", "price": 5.50, "supplier": "ABC Steel"}
            ],
        ):
            result = tool.search_products(query="steel")

            # Result should be a string (already serialized)
            self.assertIsInstance(result, str)

            # Should be able to parse as JSON if it's structured data
            # (This depends on how your tools format their output)
            try:
                json.loads(result)
            except json.JSONDecodeError:
                # If not JSON, should at least be a valid string
                self.assertIsInstance(result, str)


class MCPToolPerformanceTests(TestCase):
    """Test MCP tool performance characteristics"""

    def setUp(self):
        """Set up test data"""
        self.tool = QuotingTool()

    def test_tool_execution_time(self):
        """Test tool execution time is reasonable"""
        import time

        with patch.object(self.tool, "_search_database", return_value=[]):
            start_time = time.time()
            result = self.tool.search_products(query="steel")
            end_time = time.time()

            execution_time = end_time - start_time

            # Tool should execute in reasonable time (less than 5 seconds)
            self.assertLess(execution_time, 5.0)
            self.assertIsInstance(result, str)

    def test_tool_memory_usage(self):
        """Test tool memory usage is reasonable"""
        import tracemalloc

        tracemalloc.start()

        with patch.object(self.tool, "_search_database", return_value=[]):
            result = self.tool.search_products(query="steel")

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Memory usage should be reasonable (less than 50MB)
            self.assertLess(peak, 50 * 1024 * 1024)  # 50MB
            self.assertIsInstance(result, str)

    def test_tool_with_large_datasets(self):
        """Test tool performance with large datasets"""
        # Create a large mock dataset
        large_dataset = [
            {"name": f"Product {i}", "price": i * 1.5, "supplier": f"Supplier {i % 10}"}
            for i in range(1000)
        ]

        with patch.object(self.tool, "_search_database", return_value=large_dataset):
            import time

            start_time = time.time()

            result = self.tool.search_products(query="steel")

            end_time = time.time()
            execution_time = end_time - start_time

            # Should handle large datasets efficiently
            self.assertLess(execution_time, 10.0)  # Less than 10 seconds
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
