"""
Unit tests for MCP Quoting Tools
Run with: python manage.py test apps.quoting.tests_mcp
"""

from django.test import TestCase

from apps.client.models import Client
from apps.job.models import Job
from apps.quoting.models import SupplierProduct

from .mcp import QuotingTool, SupplierProductQueryTool


class QuotingToolTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.tool = QuotingTool()

        # Create test supplier
        self.supplier = Client.objects.create(
            name="Test Steel Co", is_supplier=True, email="test@steelco.com"
        )

        # Create test client and job
        self.client = Client.objects.create(name="Test Client", email="client@test.com")

        self.job = Job.objects.create(
            job_name="Test Job", client=self.client, description="Test metal work"
        )

        # Create test product
        self.product = SupplierProduct.objects.create(
            supplier=self.supplier,
            product_name="Steel Sheet 4x8",
            description="Cold rolled steel sheet",
            variant_price="125.50",
            price_unit="each",
            parsed_metal_type="steel",
            parsed_dimensions="4x8",
        )

    def test_search_products(self):
        """Test product search functionality"""
        result = self.tool.search_products("steel")
        self.assertIn("Test Steel Co", result)
        self.assertIn("Steel Sheet 4x8", result)
        self.assertIn("$125.50", result)

    def test_search_products_with_supplier(self):
        """Test product search with supplier filter"""
        result = self.tool.search_products("steel", "Test Steel Co")
        self.assertIn("Test Steel Co", result)

        # Search for non-existent supplier
        result = self.tool.search_products("steel", "Nonexistent")
        self.assertEqual(result, "No products found matching your search criteria.")

    def test_get_pricing_for_material(self):
        """Test material pricing lookup"""
        result = self.tool.get_pricing_for_material("steel")
        self.assertIn("Pricing for steel", result)
        self.assertIn("Test Steel Co", result)

        # Test with dimensions
        result = self.tool.get_pricing_for_material("steel", "4x8")
        self.assertIn("4x8", result)

        # Test non-existent material
        result = self.tool.get_pricing_for_material("unobtainium")
        self.assertIn("No pricing found", result)

    def test_create_quote_estimate(self):
        """Test quote estimation"""
        result = self.tool.create_quote_estimate(
            str(self.job.id), "steel sheet", labor_hours=10.0
        )

        self.assertIn("Quote Estimate for Job: Test Job", result)
        self.assertIn("Client: Test Client", result)
        self.assertIn("steel sheet", result)
        self.assertIn("Labor estimate: 10.0 hours", result)

        # Test invalid job ID
        result = self.tool.create_quote_estimate("invalid-id", "steel")
        self.assertIn("not found", result)

    def test_get_supplier_status(self):
        """Test supplier status reporting"""
        result = self.tool.get_supplier_status()
        self.assertIn("Supplier Status Report", result)
        self.assertIn("Test Steel Co", result)

        # Test specific supplier
        result = self.tool.get_supplier_status("Test Steel Co")
        self.assertIn("Test Steel Co", result)

    def test_compare_suppliers(self):
        """Test supplier comparison"""
        result = self.tool.compare_suppliers("steel")
        self.assertIn("Price Comparison for 'steel'", result)
        self.assertIn("Test Steel Co", result)

        # Test non-existent material
        result = self.tool.compare_suppliers("unobtainium")
        self.assertIn("No products found", result)


class SupplierProductQueryToolTests(TestCase):
    def setUp(self):
        self.tool = SupplierProductQueryTool()

        # Create test data
        self.supplier = Client.objects.create(
            name="Query Test Supplier", is_supplier=True
        )

        self.product = SupplierProduct.objects.create(
            supplier=self.supplier, product_name="Test Product", variant_price="99.99"
        )

    def test_get_queryset(self):
        """Test queryset with proper relations"""
        queryset = self.tool.get_queryset()
        self.assertEqual(queryset.count(), 1)

        # Test that relations are prefetched
        product = queryset.first()
        # This shouldn't trigger additional DB queries
        supplier_name = product.supplier.name
        self.assertEqual(supplier_name, "Query Test Supplier")
