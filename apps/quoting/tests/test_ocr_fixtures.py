import json
import os
import unittest
from unittest.mock import Mock, patch

from django.test import TestCase

from apps.quoting.services.providers.mistral_provider import (
    MistralPriceExtractionProvider,
)


class TestOCRFixtures(TestCase):
    """Unit tests using real OCR JSON fixtures from /tmp output."""

    def setUp(self):
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        self.ocr_dir = os.path.join(self.fixtures_dir, "ocr_responses")
        self.expected_dir = os.path.join(self.fixtures_dir, "expected_results")

    def create_mock_ocr_response(self, ocr_data):
        """Convert JSON fixture data back to mock OCR response object."""

        class MockPage:
            def __init__(self, page_data):
                self.markdown = page_data.get("markdown", "")
                self.text = page_data.get("text", "")

        class MockOCRResponse:
            def __init__(self, pages_data):
                self.pages = [MockPage(page) for page in pages_data]

        # Extract pages from the JSON structure
        pages_data = ocr_data.get("pages", [])
        return MockOCRResponse(pages_data)

    def load_ocr_fixture(self, filename):
        """Load OCR JSON fixture file."""
        filepath = os.path.join(self.ocr_dir, filename)
        if not os.path.exists(filepath):
            self.skipTest(f"OCR fixture not found: {filename}")

        with open(filepath, "r") as f:
            return json.load(f)

    @patch("apps.quoting.services.providers.mistral_provider.Mistral")
    def test_price_parsing_with_fixtures(self, mock_mistral_class):
        """Test price parsing using real OCR fixtures."""
        # Look for any OCR fixture files
        if not os.path.exists(self.ocr_dir):
            self.skipTest("No OCR fixtures directory found")

        ocr_files = [
            f for f in os.listdir(self.ocr_dir) if f.endswith("_ocr_results.json")
        ]
        if not ocr_files:
            self.skipTest("No OCR fixture files found")

        for ocr_file in ocr_files:
            with self.subTest(fixture=ocr_file):
                # Load OCR fixture
                ocr_data = self.load_ocr_fixture(ocr_file)

                # Create mock OCR response
                mock_response = self.create_mock_ocr_response(ocr_data)

                # Mock the Mistral client
                mock_client = Mock()
                mock_client.ocr.process.return_value = mock_response
                mock_mistral_class.return_value = mock_client

                # Create provider and test with mock
                provider = MistralPriceExtractionProvider(
                    api_key="dummy_key_for_testing"
                )

                # Mock file exists check and PDF encoding
                with (
                    patch("os.path.exists", return_value=True),
                    patch(
                        "apps.quoting.services.providers.mistral_provider.encode_pdf",
                        return_value="mock_base64",
                    ),
                ):
                    result, error = provider.extract_price_data("mock_file_path.pdf")

                # Basic assertions - no API calls involved
                self.assertIsNone(error, f"Parsing failed for {ocr_file}: {error}")
                self.assertIsNotNone(result, f"No result returned for {ocr_file}")

                # Check structure
                self.assertIn("supplier", result)
                self.assertIn("items", result)
                self.assertIn("raw_ocr_text", result)
                self.assertIn("parsing_stats", result)

                # Check supplier info exists
                supplier = result["supplier"]
                self.assertIn("name", supplier)

                # Check items structure
                items = result["items"]
                self.assertIsInstance(items, list)

                # If we have items, check first item structure
                if items:
                    first_item = items[0]
                    required_fields = [
                        "description",
                        "variant_id",
                        "category",
                        "product_name",
                    ]
                    for field in required_fields:
                        self.assertIn(
                            field, first_item, f"Missing field {field} in {ocr_file}"
                        )

                print(
                    f"✓ Successfully parsed {ocr_file}: {supplier['name']}, {len(items)} items"
                )


if __name__ == "__main__":
    unittest.main()
