"""
Tests for the mode-based quote generation system.

Tests the CALC, PRICE, and TABLE modes with their schemas,
tool gating, and mode inference logic.
"""

from unittest.mock import patch

from django.test import TestCase
from jsonschema import ValidationError

from apps.client.models import Client
from apps.job.models import Job
from apps.job.schemas import quote_mode_schemas
from apps.job.services.quote_mode_controller import QuoteModeController


class TestQuoteModeSchemas(TestCase):
    """Test the JSON schemas for each mode."""

    def test_calc_schema_valid(self):
        """Test valid CALC schema data."""
        valid_data = {
            "inputs": {
                "units": "mm",
                "part_dims_mm": {"L": 100, "W": 50, "T": 2},
                "qty": 10,
                "sheet_size_mm": [1220, 2440],
                "kerf_mm": 0.2,
            },
            "results": {
                "part_area_m2": 0.005,
                "total_area_m2": 0.05,
                "nest_yield_pct": 85,
                "sheets_required": 1,
                "offcut_area_m2": 2.928,
            },
            "questions": [],
        }

        schema = quote_mode_schemas.get_schema("CALC")
        # Should not raise ValidationError
        from jsonschema import validate

        validate(instance=valid_data, schema=schema)

    def test_calc_schema_invalid_missing_required(self):
        """Test CALC schema validation with missing required fields."""
        invalid_data = {
            "inputs": {"units": "mm"},
            # Missing results and questions
        }

        schema = quote_mode_schemas.get_schema("CALC")
        from jsonschema import validate

        with self.assertRaises(ValidationError):
            validate(instance=invalid_data, schema=schema)

    def test_price_schema_valid(self):
        """Test valid PRICE schema data."""
        valid_data = {
            "normalized": {
                "family": "stainless",
                "grade": "304",
                "thickness_mm": 0.9,
                "form": "sheet",
                "sheet_size_mm": [1220, 2440],
                "qty_uom": "sheet",
                "qty_required": 3,
            },
            "candidates": [
                {
                    "supplier": "XYZ Metals",
                    "sku": "SS304-0.9-1220x2440",
                    "uom": "sheet",
                    "price_per_uom": 189.00,
                    "lead_time_days": 2,
                    "delivery": 25.00,
                    "notes": "BA finish",
                }
            ],
            "questions": [],
        }

        schema = quote_mode_schemas.get_schema("PRICE")
        from jsonschema import validate

        validate(instance=valid_data, schema=schema)

    def test_table_schema_valid(self):
        """Test valid TABLE schema data."""
        valid_data = {
            "rows": [
                {
                    "item": "SS304 Sheet",
                    "qty": 3,
                    "uom": "sheet",
                    "unit_cost": 189.00,
                    "subtotal": 567.00,
                }
            ],
            "totals": {
                "material": 567.00,
                "labour": 235.40,
                "freight": 25.00,
                "overheads": 28.00,
                "markup_pct": 15,
                "grand_total_ex_gst": 983.71,
            },
            "markdown": "| Item | Qty | Unit | Cost |\n|------|-----|------|------|\n",
            "questions": [],
        }

        schema = quote_mode_schemas.get_schema("TABLE")
        from jsonschema import validate

        validate(instance=valid_data, schema=schema)

    def test_get_allowed_tools(self):
        """Test tool gating for each mode."""
        # CALC mode should have no tools
        calc_tools = quote_mode_schemas.get_allowed_tools("CALC")
        self.assertEqual(calc_tools, [])

        # PRICE mode should have pricing tools
        price_tools = quote_mode_schemas.get_allowed_tools("PRICE")
        self.assertIn("search_products", price_tools)
        self.assertIn("get_pricing_for_material", price_tools)
        self.assertIn("compare_suppliers", price_tools)

        # TABLE mode should have no tools
        table_tools = quote_mode_schemas.get_allowed_tools("TABLE")
        self.assertEqual(table_tools, [])


class TestQuoteModeController(TestCase):
    """Test the QuoteModeController functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.controller = QuoteModeController()

        # Create test job
        self.client_obj = Client.objects.create(
            name="Test Client", email="test@example.com"
        )
        self.job = Job.objects.create(
            name="Test Job", job_number="TEST001", client=self.client_obj
        )

    def test_mode_inference_calc(self):
        """Test mode inference for CALC-related inputs."""
        test_inputs = [
            "Calculate the area for 100x50mm parts",
            "How many sheets do I need for 20 parts?",
            "What's the yield for nesting these dimensions?",
            "Calculate sheet requirements with 0.2mm kerf",
        ]

        for input_text in test_inputs:
            mode, confidence = self.controller.infer_mode(input_text)
            self.assertEqual(mode, "CALC", f"Failed to infer CALC for: {input_text}")

    def test_mode_inference_price(self):
        """Test mode inference for PRICE-related inputs."""
        test_inputs = [
            "What's the price for 304 stainless?",
            "Find suppliers for aluminum sheet",
            "Get pricing for steel angle",
            "Compare costs from different suppliers",
        ]

        for input_text in test_inputs:
            mode, confidence = self.controller.infer_mode(input_text)
            self.assertEqual(mode, "PRICE", f"Failed to infer PRICE for: {input_text}")

    def test_mode_inference_table(self):
        """Test mode inference for TABLE-related inputs."""
        test_inputs = [
            "Generate the final quote table",
            "Show me the summary",
            "What's the grand total?",
            "Create invoice breakdown",
        ]

        for input_text in test_inputs:
            mode, confidence = self.controller.infer_mode(input_text)
            self.assertEqual(mode, "TABLE", f"Failed to infer TABLE for: {input_text}")

    def test_system_prompt(self):
        """Test that system prompt is appropriate for mode-based operation."""
        prompt = self.controller.get_system_prompt()

        # Check for key mode-related instructions
        self.assertIn("MODE=CALC", prompt)
        self.assertIn("MODE=PRICE", prompt)
        self.assertIn("MODE=TABLE", prompt)
        self.assertIn("Never call tools in the wrong mode", prompt)
        self.assertIn("strict JSON", prompt)

    def test_render_prompt(self):
        """Test prompt rendering for each mode."""
        # Test CALC prompt
        calc_prompt = self.controller.render_prompt(
            mode="CALC",
            user_input="Calculate area for 100x50mm",
            job_ctx={"job_number": "TEST001", "client": "Test Client"},
        )
        self.assertIn("MODE=CALC", calc_prompt)
        self.assertIn("SCHEMA:", calc_prompt)
        self.assertIn("TEST001", calc_prompt)

        # Test PRICE prompt
        price_prompt = self.controller.render_prompt(
            mode="PRICE", user_input="Price 304 stainless", job_ctx=None
        )
        self.assertIn("MODE=PRICE", price_prompt)
        self.assertIn("Map to SKUs", price_prompt)

        # Test TABLE prompt
        table_prompt = self.controller.render_prompt(
            mode="TABLE", user_input="Generate summary", job_ctx=None
        )
        self.assertIn("MODE=TABLE", table_prompt)
        self.assertIn("Calculate subtotals", table_prompt)

    def test_validate_json(self):
        """Test JSON validation against schemas."""
        # Valid data should pass
        valid_calc_data = {
            "inputs": {"units": "mm"},
            "results": {},
            "questions": ["What are the dimensions?"],
        }
        validated = self.controller.validate_json(
            valid_calc_data, self.controller.schemas["CALC"]
        )
        self.assertEqual(validated, valid_calc_data)

        # Invalid data should raise ValidationError
        invalid_data = {"wrong": "structure"}
        with self.assertRaises(ValidationError):
            self.controller.validate_json(invalid_data, self.controller.schemas["CALC"])

    def test_get_mcp_tools_for_mode(self):
        """Test that correct tools are returned for each mode."""
        # CALC mode - no tools
        calc_tools = self.controller.get_mcp_tools_for_mode("CALC")
        self.assertEqual(len(calc_tools), 0)

        # PRICE mode - pricing tools
        price_tools = self.controller.get_mcp_tools_for_mode("PRICE")
        self.assertEqual(len(price_tools), 3)
        tool_names = [tool.name for tool in price_tools]
        self.assertIn("search_products", tool_names)
        self.assertIn("get_pricing_for_material", tool_names)
        self.assertIn("compare_suppliers", tool_names)

        # TABLE mode - no tools
        table_tools = self.controller.get_mcp_tools_for_mode("TABLE")
        self.assertEqual(len(table_tools), 0)

    @patch("apps.job.services.quote_mode_controller.logger")
    def test_run_without_gemini_client(self, mock_logger):
        """Test run method returns mock data when no Gemini client provided."""
        # Test CALC mode
        calc_data, has_questions = self.controller.run(
            mode="CALC", user_input="Calculate area", job=self.job, gemini_client=None
        )
        self.assertTrue(has_questions)
        self.assertIn("questions", calc_data)
        self.assertTrue(len(calc_data["questions"]) > 0)

        # Test PRICE mode
        price_data, has_questions = self.controller.run(
            mode="PRICE", user_input="Price stainless", job=None, gemini_client=None
        )
        self.assertTrue(has_questions)
        self.assertIn("normalized", price_data)
        self.assertIn("candidates", price_data)

        # Test TABLE mode
        table_data, has_questions = self.controller.run(
            mode="TABLE", user_input="Create table", job=None, gemini_client=None
        )
        self.assertTrue(has_questions)
        self.assertIn("rows", table_data)
        self.assertIn("totals", table_data)

    def test_invalid_mode(self):
        """Test that invalid mode raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.controller.run(mode="INVALID", user_input="Test", job=None)
        self.assertIn("Invalid mode", str(context.exception))
