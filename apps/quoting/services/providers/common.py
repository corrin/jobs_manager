"""Common utilities for AI price extraction providers."""

import logging

logger = logging.getLogger(__name__)


def create_extraction_prompt() -> str:
    """Generates a comprehensive prompt for supplier price list data extraction."""
    return """Extract supplier price list data from this document and return it in the following JSON format:
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
    if hasattr(usage, "input_tokens"):
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
    elif hasattr(usage, "prompt_tokens"):
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
    elif isinstance(usage, dict):
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
    else:
        input_tokens = 0
        output_tokens = 0

    total_tokens = input_tokens + output_tokens

    logger.info(
        f"{api_name} API token usage for price list extraction: "
        f"Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}"
    )
