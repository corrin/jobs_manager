"""
JSON schemas for mode-based quote generation.

Defines structured input/output contracts for CALC, PRICE, and TABLE modes
to ensure consistent data handling and validation.
"""

CALC_SCHEMA = {
    "type": "object",
    "required": ["inputs", "results", "questions"],
    "properties": {
        "inputs": {
            "type": "object",
            "required": ["units"],
            "properties": {
                "units": {
                    "type": "string",
                    "enum": ["mm", "m"],
                    "description": "Unit system for measurements",
                },
                "part_dims_mm": {
                    "type": "object",
                    "properties": {
                        "L": {"type": "number", "description": "Length in mm"},
                        "W": {"type": "number", "description": "Width in mm"},
                        "T": {"type": "number", "description": "Thickness in mm"},
                        "OD": {"type": "number", "description": "Outer diameter in mm"},
                        "ID": {"type": "number", "description": "Inner diameter in mm"},
                    },
                    "description": "Part dimensions",
                },
                "qty": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Quantity of parts needed",
                },
                "sheet_size_mm": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Sheet dimensions [length, width] in mm",
                },
                "kerf_mm": {
                    "type": "number",
                    "description": "Cutting kerf width in mm",
                },
            },
        },
        "results": {
            "type": "object",
            "properties": {
                "part_area_m2": {
                    "type": "number",
                    "description": "Area of single part in m²",
                },
                "total_area_m2": {
                    "type": "number",
                    "description": "Total area for all parts in m²",
                },
                "nest_yield_pct": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Nesting efficiency percentage",
                },
                "sheets_required": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of sheets needed",
                },
                "offcut_area_m2": {
                    "type": "number",
                    "description": "Waste material area in m²",
                },
            },
        },
        "questions": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
            "description": "Clarifying questions for missing/ambiguous data",
        },
    },
}

PRICE_SCHEMA = {
    "type": "object",
    "required": ["normalized", "candidates", "questions"],
    "properties": {
        "normalized": {
            "type": "object",
            "required": ["family", "grade", "thickness_mm", "form"],
            "properties": {
                "family": {
                    "type": "string",
                    "description": "Material family (e.g., stainless, aluminum)",
                },
                "grade": {
                    "type": "string",
                    "description": "Material grade (e.g., 304, 316, 5083)",
                },
                "thickness_mm": {
                    "type": "number",
                    "description": "Material thickness in mm",
                },
                "form": {
                    "type": "string",
                    "enum": ["sheet", "plate", "tube", "angle", "bar"],
                    "description": "Material form factor",
                },
                "sheet_size_mm": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Sheet dimensions if applicable",
                },
                "qty_uom": {
                    "type": "string",
                    "enum": ["sheet", "kg", "m", "each"],
                    "description": "Quantity unit of measure",
                },
                "qty_required": {"type": "number", "description": "Quantity needed"},
            },
        },
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["supplier", "sku", "uom", "price_per_uom"],
                "properties": {
                    "supplier": {
                        "type": "string",
                        "description": "Supplier name or STOCK for inventory",
                    },
                    "sku": {
                        "type": "string",
                        "description": "Product SKU or stock code",
                    },
                    "uom": {
                        "type": "string",
                        "description": "Unit of measure for pricing",
                    },
                    "price_per_uom": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Price per unit",
                    },
                    "lead_time_days": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Lead time in days",
                    },
                    "delivery": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Delivery cost",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes (finish, location, etc.)",
                    },
                },
            },
            "description": "Matching products from suppliers",
        },
        "questions": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
            "description": "Clarifying questions for specifications",
        },
    },
}

TABLE_SCHEMA = {
    "type": "object",
    "required": ["rows", "totals", "markdown", "questions"],
    "properties": {
        "rows": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["item", "qty", "uom", "unit_cost", "subtotal"],
                "properties": {
                    "item": {"type": "string", "description": "Line item description"},
                    "qty": {"type": "number", "minimum": 0, "description": "Quantity"},
                    "uom": {"type": "string", "description": "Unit of measure"},
                    "unit_cost": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Cost per unit",
                    },
                    "subtotal": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Line total (qty × unit_cost)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes for this line",
                    },
                },
            },
            "description": "Quote line items",
        },
        "totals": {
            "type": "object",
            "required": [
                "material",
                "labour",
                "freight",
                "overheads",
                "markup_pct",
                "grand_total_ex_gst",
            ],
            "properties": {
                "material": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Total material cost",
                },
                "labour": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Total labour cost",
                },
                "freight": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Total freight/delivery cost",
                },
                "overheads": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Overhead costs",
                },
                "markup_pct": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Markup percentage",
                },
                "grand_total_ex_gst": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Grand total excluding GST",
                },
            },
        },
        "markdown": {
            "type": "string",
            "description": "Formatted markdown table for display",
        },
        "questions": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 1,
            "description": "Final clarifications if needed",
        },
    },
}


def get_schema(mode: str) -> dict:
    """
    Get the JSON schema for a specific mode.

    Args:
        mode: One of "CALC", "PRICE", or "TABLE"

    Returns:
        The corresponding JSON schema dictionary

    Raises:
        ValueError: If mode is not recognized
    """
    schemas = {"CALC": CALC_SCHEMA, "PRICE": PRICE_SCHEMA, "TABLE": TABLE_SCHEMA}

    if mode not in schemas:
        raise ValueError(f"Unknown mode: {mode}. Must be one of {list(schemas.keys())}")

    return schemas[mode]


def get_allowed_tools(mode: str) -> list:
    """
    Get the list of allowed MCP tools for a specific mode.

    Args:
        mode: One of "CALC", "PRICE", or "TABLE"

    Returns:
        List of allowed tool names for the mode

    Raises:
        ValueError: If mode is not recognized
    """
    tools = {
        "CALC": [],  # No tools needed for calculations
        "PRICE": ["search_products", "get_pricing_for_material", "compare_suppliers"],
        "TABLE": [],  # No tools needed for formatting
    }

    if mode not in tools:
        raise ValueError(f"Unknown mode: {mode}. Must be one of {list(tools.keys())}")

    return tools[mode]
