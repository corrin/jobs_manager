#!/usr/bin/env python
import os
import sys

import django

from apps.quoting.services.gemini_price_list_extraction import (
    extract_data_from_supplier_price_list_gemini,
)
from apps.workflow.models import AIProvider

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings.local")
django.setup()


def test_pdf_parsing():
    """Test PDF parsing functionality with sample files."""
    pdf_dir = "/home/corrin/src/jobs_manager/docs/test_pdfs/price_lists"
    pdf_files = [
        "Copy of ST Flat Product Morris sheetmetal 5.05.2025 1.pdf",
        "Morris SM - Extrusions & Rolled Stock.pdf",
        "WM Aluminium & Stainless Steel Price List Pricing 42AS22 01-05-25.pdf",
        "RATE CARD - APRIL 2025.pdf",
    ]

    # Check if we have API credentials
    try:
        ai_provider = AIProvider.objects.filter(default=True).first()
        print(f"AI Provider: {ai_provider.provider_type}")
        print(f"API Key configured: {'Yes' if ai_provider.api_key else 'No'}")
    except Exception as e:
        print(f"Error getting AI provider: {e}")
        return

    # Test each PDF
    for pdf_file in pdf_files:
        file_path = os.path.join(pdf_dir, pdf_file)
        if os.path.exists(file_path):
            print(f"\n{'='*60}")
            print(f"Testing: {pdf_file}")
            print(f"{'='*60}")

            try:
                result = extract_data_from_supplier_price_list_gemini(file_path)
                if result:
                    print("Success! Extracted data:")
                    print(
                        f"Supplier: {result.get('supplier', {}).get('name', 'Unknown')}"
                    )
                    print(f"Number of items: {len(result.get('items', []))}")
                    if result.get("items"):
                        print(
                            f"First item: {result['items'][0].get('description', 'No description')}"
                        )
                else:
                    print("Failed to extract data - result is None")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print(f"File not found: {file_path}")


if __name__ == "__main__":
    test_pdf_parsing()
