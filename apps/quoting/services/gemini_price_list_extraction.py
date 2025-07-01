import json
import logging
from typing import Optional, Tuple

import google.generativeai as genai
import pdfplumber

from apps.workflow.enums import AIProviderTypes
from apps.workflow.models import AIProvider

logger = logging.getLogger(__name__)


def read_file_content(file_path: str) -> Optional[bytes]:
    """Read file content in binary mode."""
    try:
        with open(file_path, "rb") as file:
            return file.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None


def create_concise_prompt(metal_types: list[str]) -> str:
    """Generates a concise prompt for Supplier Price List data extraction."""
    metal_types_str = ", ".join(metal_types)
    return f"Extract supplier price list data for {metal_types_str} and return it in JSON format."


def create_supplier_extraction_prompt() -> str:
    """Generates a comprehensive prompt for supplier price list data extraction."""
    s = """Extract supplier price list data from this document and return it in the following JSON format:
        {
        "supplier": {
        "name": "Supplier Name",
        "customer": "Customer name if shown",
        "date": "Date if shown (YYYY-MM-DD format)"
        },
        "items": [
        {
        "description": "EXACT raw text description from price list",
        "unit_price": "123.45",
        "supplier_item_code": "Item code/SKU if available",
        "variant_id": "Unique identifier for this specific variant",
        "metal_type": "Steel, Aluminum, Galvanised Steel, Stainless Steel, etc.",
        "dimensions": "Dimensions as shown",
        "specifications": "Technical specs like alloy, temper, finish"
        }
        ]
        }

        Steel Sheet Example (P-codes, metre dimensions):
        Input: Item: P0070416, Thick: 0.5, Width: 1.219, Length: 2.438, Price: $29.40

        Output:
        {
        "description": "P0070416 0.5 1.219 2.438 11.660 $29.40",
        "unit_price": "29.40",
        "supplier_item_code": "P0070416",
        "variant_id": "P0070416-0.5-1.219-2.438",
        "metal_type": "Galvanised Steel",
        "dimensions": "0.5mm x 1.219m x 2.438m",
        "specifications": "Thickness: 0.5mm, Weight: 11.660kg/sheet"
        }

        Aluminum Example (UA codes, mm dimensions):
        Input: Description: 0.7mm X 1200 X 2400 Sheet 5005 H34 50µm PE Film, Price: $49.35

        Output:
        {
        "description": "0.7mm X 1200 X 2400 Sheet 5005 H34 50µm PE Film $49.35",
        "unit_price": "49.35",
        "supplier_item_code": "",
        "variant_id": "5005-0.7-1200-2400-H34-50µm",
        "metal_type": "Aluminum",
        "dimensions": "0.7mm x 1200mm x 2400mm",
        "specifications": "5005 alloy, H34 temper, 50µm PE Film"
        }

        Aluminum Profile Example (UA codes):
        Input: Description: 10 X 2.3mm UA1165 AEC3799 FLAT BAR 6060T5 5.000 m, Price: $8.98

        Output:
        {
        "description": "10 X 2.3mm UA1165 AEC3799 FLAT BAR 6060T5 5.000 m $8.98",
        "unit_price": "8.98",
        "supplier_item_code": "UA1165",
        "variant_id": "UA1165-10-2.3",
        "metal_type": "Aluminum",
        "dimensions": "10mm x 2.3mm x 5.000m",
        "specifications": "6060T6 alloy, Flat Bar profile"
        }

        CRITICAL RULES:

        Extract descriptions EXACTLY as they appear in the document
        Remove currency symbols from unit_price (no $ signs)
        Create unique variant_id for each product variant
        Do not guess - if information isn't clear, leave field empty
        Extract ALL products from the entire document
        Use consistent metal_type values within the same category
        Return ONLY valid JSON - no explanatory text
        Variant ID Rules:

        Steel with P-codes: P-code + dimensions (P0070416-0.5-1.219-2.438)
        Aluminum sheets: alloy-thickness-width-length-temper-coating (5005-0.7-1200-2400-H34-50µm)
        Aluminum profiles: UA-code + key dimensions (UA1165-10-2.3)
        Metal Type Detection:

        Look for category headers: "GALVANISED SHEET" → "Galvanised Steel"
        Look for alloy numbers: "5005", "6060T5" → "Aluminum"
        Look for material codes: "COLD ROLLED" → "Steel"
        Extract every single product from all pages. Return only the JSON object."""
    return s


def clean_json_response(text: str) -> str:
    """Clean up JSON response by removing markdown code blocks."""
    text = text.strip()

    if "```json" in text:
        text = text.split("```json")[1]
        if "```" in text:
            text = text.split("```")[0]
    elif "```" in text:
        text = text.replace("```", "")

    return text.strip()


def log_token_usage(usage, api_name):
    """Log token usage from AI API response."""
    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)
    total_tokens = input_tokens + output_tokens

    logger.info(
        f"{api_name} API token usage for price list extraction: "
        f"Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}"
    )


def extract_data_from_supplier_price_list_gemini(
    file_path: str, content_type: Optional[str] = None
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Extract data from a supplier price list file using Gemini.

    Args:
        file_path: Path to the price list file.
        content_type: MIME type of the file (e.g., 'application/pdf', 'image/jpeg').

    Returns:
        Tuple[Optional[dict], Optional[str]]: A tuple containing the extracted data as a dictionary
                                               and an error message (if any).
    """
    try:
        default_ai_provider = AIProvider.objects.filter(default=True).first()

        if not default_ai_provider:
            return (
                None,
                "No active AI provider configured. Please set one in company settings.",
            )

        if default_ai_provider.provider_type != AIProviderTypes.GOOGLE:
            return (
                None,
                f"Configured AI provider is {default_ai_provider.provider_type}, but this function requires Google (Gemini).",
            )

        gemini_api_key = default_ai_provider.api_key

        if not gemini_api_key:
            return (
                None,
                "Gemini API key not configured for the active AI provider. Please add it in company settings.",
            )

        genai.configure(api_key=gemini_api_key)

        # Configure generation with high token limit for large supplier catalogs
        generation_config = genai.GenerationConfig(
            max_output_tokens=200000,  # Required for catalogs with thousands of products
            temperature=0.1,  # Lower temperature for more consistent extraction
        )

        # Get the Gemini AI provider and model name
        ai_provider = AIProvider.objects.filter(
            provider_type=AIProviderTypes.GOOGLE
        ).first()
        if not ai_provider or not ai_provider.model_name:
            raise ValueError("No Gemini AI provider configured with model_name")

        model = genai.GenerativeModel(
            ai_provider.model_name, generation_config=generation_config
        )

        # Extract text from PDF using pdfplumber
        text_pages = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if not page_text:
                    return None, f"Failed to extract text from page {page_num} of PDF"
                text_pages.append(page_text)

        extracted_text = "\n\n".join(text_pages)
        logger.info(f"Extracted {len(extracted_text)} characters from PDF")

        # Send extracted text to Gemini
        prompt = create_supplier_extraction_prompt()
        contents = [f"{prompt}\n\nExtracted text from PDF:\n{extracted_text}"]

        logger.info(f"Calling Gemini API for price list extraction: {file_path}")
        response = model.generate_content(contents)

        # Log token usage
        if response.usage_metadata:
            log_token_usage(response.usage_metadata, "Gemini")
        else:
            logger.warning("Gemini API response did not contain usage_metadata.")

        if not response.candidates:
            return None, "Gemini API returned no candidates."

        # Extract JSON from response
        json_text = response.text

        price_list_data = json.loads(clean_json_response(json_text))

        # No supplier matching needed here, as this is for price lists, not specific quotes.
        # The supplier name will be extracted directly from the JSON.

        return price_list_data, None

    except json.JSONDecodeError as e:
        logger.error(f"Gemini response was not valid JSON: {json_text}. Error: {e}")
        return None, f"Gemini returned invalid JSON: {e}"
    except Exception as e:
        logger.exception(
            f"Error extracting data from supplier price list with Gemini: {e}"
        )
        return None, str(e)
