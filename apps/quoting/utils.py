import hashlib
import math
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from apps.quoting.models import SupplierProduct


def calculate_product_mapping_hash(product_data: Dict[str, Any]) -> str:
    """
    Calculate SHA-256 hash for product mapping based on description.

    This function ensures consistent hash calculation across the system
    for linking SupplierProduct records to ProductParsingMapping records.

    Args:
        product_data: Dictionary containing product information

    Returns:
        SHA-256 hash string (64 characters)
    """
    description = str(
        product_data.get("description", "") or product_data.get("product_name", "")
    )
    return hashlib.sha256(description.encode()).hexdigest()


def calculate_supplier_product_hash(supplier_product: "SupplierProduct") -> str:
    """
    Calculate SHA-256 hash for a SupplierProduct instance.

    Args:
        supplier_product: SupplierProduct model instance

    Returns:
        SHA-256 hash string (64 characters)
    """
    product_data = {
        "description": supplier_product.description or "",
        "product_name": supplier_product.product_name or "",
    }
    return calculate_product_mapping_hash(product_data)


def calculate_sheet_tenths(
    part_width_mm: float,
    part_height_mm: float,
    sheet_width_mm: float = 1200.0,
    sheet_height_mm: float = 2400.0,
) -> int:
    """
    Calculate how many "tenths" of a sheet a part will occupy.

    A sheet is divided into a 5x2 grid (10 sections):
    - Each section is (sheet_width/2) x (sheet_height/5) mm
    - For standard 1200x2400mm sheet: 600mm x 480mm per section

    If any part of the cut touches a section, that section counts as used.
    This is a simple grid-based nesting calculation for quoting purposes.

    Args:
        part_width_mm: Width of the part in millimeters
        part_height_mm: Height of the part in millimeters
        sheet_width_mm: Width of the full sheet (default: 1200mm)
        sheet_height_mm: Height of the full sheet (default: 2400mm)

    Returns:
        Number of tenths (sections) the part will span across

    Raises:
        ValueError: If dimensions are invalid

    Examples:
        >>> calculate_sheet_tenths(400, 300)  # Fits in 1 section
        1
        >>> calculate_sheet_tenths(700, 700)  # Spans 2x2 = 4 sections
        4
        >>> calculate_sheet_tenths(650, 450)  # Spans 2x1 = 2 sections
        2
        >>> calculate_sheet_tenths(1100, 500)  # Spans 2x2 = 4 sections (full width)
        4
    """
    if part_width_mm <= 0 or part_height_mm <= 0:
        raise ValueError("Part dimensions must be positive")

    if sheet_width_mm <= 0 or sheet_height_mm <= 0:
        raise ValueError("Sheet dimensions must be positive")

    if part_width_mm > sheet_width_mm or part_height_mm > sheet_height_mm:
        raise ValueError(
            f"Part dimensions ({part_width_mm}x{part_height_mm}mm) exceed "
            f"sheet dimensions ({sheet_width_mm}x{sheet_height_mm}mm)"
        )

    # Calculate section dimensions
    section_width = sheet_width_mm / 2  # 2 columns
    section_height = sheet_height_mm / 5  # 5 rows

    # Calculate how many sections the part spans in each direction
    # Use ceiling division: if part touches any part of a section, it uses that section
    sections_wide = math.ceil(part_width_mm / section_width)
    sections_tall = math.ceil(part_height_mm / section_height)

    # Total sections used is the product
    total_sections = sections_wide * sections_tall

    return total_sections
