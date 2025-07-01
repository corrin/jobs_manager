import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.purchasing.models import Stock
from apps.quoting.services.product_parser import ProductParser

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Stock)
def auto_parse_stock_item(sender, instance, created, **kwargs):
    """
    Automatically parse Stock items when they're created or updated.
    Many inventory items only have descriptions and missing details like
    metal_type, alloy, specifics that can be inferred from the description.
    """
    if not created and instance.parsed_at:
        # Skip if this is an update and it's already been parsed
        return

    try:
        # Prepare stock data for parsing - use description as main input
        stock_data = {
            "product_name": instance.description or "",
            "description": instance.description or "",
            "specifications": instance.specifics or "",
            "item_no": instance.item_code or "",
            "variant_id": f"stock-{instance.id}",  # Unique identifier
            "variant_width": "",
            "variant_length": "",
            "variant_price": instance.unit_cost,
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

            if not instance.metal_type or instance.metal_type == "unspecified":
                if parsed_data.get("metal_type"):
                    updates["metal_type"] = parsed_data["metal_type"]

            if not instance.alloy:
                if parsed_data.get("alloy"):
                    updates["alloy"] = parsed_data["alloy"]

            if not instance.specifics:
                if parsed_data.get("specifics"):
                    updates["specifics"] = parsed_data["specifics"]

            # Always update item_code if we have a better one
            if parsed_data.get("item_code") and not instance.item_code:
                updates["item_code"] = parsed_data["item_code"]

            # Apply updates
            Stock.objects.filter(id=instance.id).update(**updates)
            status = "from cache" if was_cached else "newly parsed"
            updated_fields = [
                k
                for k in updates.keys()
                if k not in ["parsed_at", "parser_version", "parser_confidence"]
            ]
            logger.info(
                f"Auto-parsed stock item {instance.id} ({status}): {updated_fields}"
            )
        else:
            logger.warning(f"Failed to auto-parse stock item {instance.id}")

    except Exception as e:
        logger.exception(f"Error auto-parsing stock item {instance.id}: {e}")
