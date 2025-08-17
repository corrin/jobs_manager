import logging

from django.utils import timezone

from apps.purchasing.models import Stock
from apps.quoting.services.product_parser import ProductParser

logger = logging.getLogger(__name__)


def auto_parse_stock_item(stock_instance):
    """
    Parse Stock items to extract metal_type, alloy, and specifics from description.
    Call this explicitly when creating new stock items that need parsing.
    """
    # Skip if already parsed
    if stock_instance.parsed_at:
        return

    try:
        # Prepare stock data for parsing - use description as main input
        stock_data = {
            "product_name": stock_instance.description or "",
            "description": stock_instance.description or "",
            "specifications": stock_instance.specifics or "",
            "item_no": stock_instance.item_code or "",
            "variant_id": f"stock-{stock_instance.id}",  # Unique identifier
            "variant_width": "",
            "variant_length": "",
            "variant_price": stock_instance.unit_cost,
            "price_unit": "each",  # Default for stock items
        }

        # Parse the stock item
        parser = ProductParser()
        parsed_data, was_cached = parser.parse_product(stock_data)

        if parsed_data:
            # Only update fields that are currently blank/unspecified
            updates = {
                "parsed_at": timezone.now(),
                "parser_version": parsed_data.get("parser_version"),
                "parser_confidence": parsed_data.get("confidence"),
            }

            if (
                not stock_instance.metal_type
                or stock_instance.metal_type == "unspecified"
            ):
                if parsed_data.get("metal_type"):
                    updates["metal_type"] = parsed_data["metal_type"]

            if not stock_instance.alloy:
                if parsed_data.get("alloy"):
                    updates["alloy"] = parsed_data["alloy"]

            if not stock_instance.specifics:
                if parsed_data.get("specifics"):
                    updates["specifics"] = parsed_data["specifics"]

            # Always update item_code if we have a better one
            if parsed_data.get("item_code") and not stock_instance.item_code:
                updates["item_code"] = parsed_data["item_code"]

            # Apply updates
            Stock.objects.filter(id=stock_instance.id).update(**updates)

            # Generate item_code if still missing after parsing
            stock_instance.refresh_from_db()
            if not stock_instance.item_code or not stock_instance.item_code.strip():
                from apps.workflow.api.xero.stock_sync import generate_item_code

                generated_code = generate_item_code(stock_instance)
                Stock.objects.filter(id=stock_instance.id).update(
                    item_code=generated_code
                )
                logger.info(
                    f"Generated item_code '{generated_code}' for stock item {stock_instance.id}"
                )

            status = "from cache" if was_cached else "newly parsed"
            updated_fields = [
                k
                for k in updates.keys()
                if k not in ["parsed_at", "parser_version", "parser_confidence"]
            ]
            logger.info(
                f"Parsed stock item {stock_instance.id} ({status}): {updated_fields}"
            )
        else:
            logger.warning(f"Failed to parse stock item {stock_instance.id}")

    except Exception as e:
        logger.exception(f"Error parsing stock item {stock_instance.id}: {e}")
