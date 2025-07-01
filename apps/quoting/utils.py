import hashlib
from typing import Any, Dict


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


def calculate_supplier_product_hash(supplier_product) -> str:
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
