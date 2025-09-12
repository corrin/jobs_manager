import logging
import time
from typing import Any, Dict, Optional

from django.db import models
from django.utils import timezone
from xero_python.accounting import AccountingApi

from apps.purchasing.models import Stock
from apps.workflow.api.xero.xero import api_client, get_tenant_id
from apps.workflow.models import XeroAccount
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger("xero")
SLEEP_TIME = 1  # Sleep after every API call to avoid hitting rate limits


def _escape_where_value(v: str) -> str:
    return v.replace('"', r"\"")


def get_xero_item_by_code(api: AccountingApi, tenant_id: str, code: str):
    if not code:
        return None
    try:
        where = f'Code=="{_escape_where_value(code)}"'
        resp = api.get_items(tenant_id, where=where)
        time.sleep(SLEEP_TIME)
        items = getattr(resp, "items", None) or getattr(resp, "Items", None) or []
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Failed to fetch Xero item by code '{code}': {e}")
        return None


def generate_item_code(stock_item: Stock) -> str:
    """
    Generate a valid item code for a stock item based on its properties.

    Args:
        stock_item: Stock instance to generate code for

    Returns:
        str: Generated item code
    """
    # Try to use parsed item_code first
    if stock_item.item_code and stock_item.item_code.strip():
        return stock_item.item_code.strip()

    # Generate based on metal type, alloy, and specifics
    parts = []

    # Metal type prefix
    # Should ALWAYS be based on MetalType (apps.job.enums)
    metal_map = {
        "mild_steel": "MS",
        "stainless_steel": "SS",
        "aluminium": "AL",
        "brass": "BR",
        "copper": "CU",
        "titanium": "TI",
        "zinc": "ZN",
        "galvanised": "GAL",
        "other": "OT",
        "unspecified": "UN",
    }

    metal_prefix = metal_map.get(stock_item.metal_type, "UN")
    parts.append(metal_prefix)

    # Add alloy if available
    if stock_item.alloy and stock_item.alloy.strip():
        alloy_clean = stock_item.alloy.strip().replace(" ", "").upper()[:6]
        parts.append(alloy_clean)

    # Add specifics if available (truncated)
    if stock_item.specifics and stock_item.specifics.strip():
        specifics_clean = stock_item.specifics.strip().replace(" ", "").upper()[:10]
        parts.append(specifics_clean)

    # If no meaningful parts, use stock ID (shortened)
    if len(parts) == 1 and parts[0] == "UN":
        parts = ["STK", str(stock_item.id)[:8]]

    # Join with hyphens and ensure max length (Xero limit is 30 characters)
    item_code = "-".join(parts)[:30]

    return item_code


def validate_stock_for_xero(stock_item: Stock) -> bool:
    """
    Validate if a stock item is ready for Xero sync.

    Args:
        stock_item: Stock instance to validate

    Returns:
        bool: True if valid for sync
    """
    if not stock_item.description or not stock_item.description.strip():
        logger.warning(f"Stock item {stock_item.id} missing description")
        return False

    if stock_item.unit_cost is None or stock_item.unit_cost < 0:
        logger.warning(
            f"Stock item {stock_item.id} has invalid unit_cost: {stock_item.unit_cost}"
        )
        return False

    return True


def sync_stock_to_xero(stock_item: Stock) -> bool:
    """
    Push a stock item to Xero as an inventory item.

    Args:
        stock_item: Stock instance to sync

    Returns:
        bool: True if successful
    """
    # Initial validation to fail fast
    if not validate_stock_for_xero(stock_item):
        logger.error(f"Stock item {stock_item.id} failed validation for Xero sync")
        return False

    if not (stock_item.item_code and stock_item.item_code.strip()):
        stock_item.item_code = generate_item_code(stock_item)
        stock_item.save(update_fields=["item_code"])
        logger.info(
            f"Generated item_code '{stock_item.item_code}' for stock {stock_item.id}"
        )

    api = AccountingApi(api_client)
    tenant_id = get_tenant_id()

    purchase_account = (
        XeroAccount.objects.filter(account_code="300").first()
        or XeroAccount.objects.filter(
            account_type__in=["EXPENSE", "DIRECTCOSTS"]
        ).first()
    )
    sales_account = (
        XeroAccount.objects.filter(account_code="200").first()
        or XeroAccount.objects.filter(
            account_type__in=["REVENUE", "OTHERINCOME"]
        ).first()
    )

    item_data = {
        "Code": stock_item.item_code,
        "Name": (stock_item.description or "")[:50],
        "Description": stock_item.description,
        "IsTrackedAsInventory": True,
        "QuantityOnHand": float(stock_item.quantity),
    }

    if purchase_account and stock_item.unit_cost is not None:
        item_data["PurchaseDetails"] = {
            "UnitPrice": float(stock_item.unit_cost),
            "AccountCode": purchase_account.account_code,
        }
    else:
        logger.warning(
            f"Missing purchase account or unit_cost for stock {stock_item.id}"
        )

    if stock_item.unit_revenue and stock_item.unit_revenue > 0 and sales_account:
        item_data["SalesDetails"] = {
            "UnitPrice": float(stock_item.unit_revenue),
            "AccountCode": sales_account.account_code,
        }
    else:
        logger.warning(
            f"Missing sales account or unit_revenue for stock {stock_item.id}: "
            f"unit_revenue={stock_item.unit_revenue}, sales_account={sales_account}"
        )

    logger.info(f"Sending item data to Xero: {item_data}")

    try:
        # 1) If we don't have xero_id, try to find by Code first
        if not stock_item.xero_id:
            existing = get_xero_item_by_code(api, tenant_id, stock_item.item_code)
            if existing:
                stock_item.xero_id = existing.item_id
                stock_item.xero_last_modified = timezone.now()
                stock_item.save(update_fields=["xero_id", "xero_last_modified"])
                logger.info(
                    f"Linked local stock {stock_item.id} to existing Xero item {stock_item.xero_id} by Code"
                )

        # 2) If we already have xero_id -> update; else -> create
        if stock_item.xero_id:
            item_data["ItemID"] = stock_item.xero_id
            api.update_item(
                tenant_id, item_id=stock_item.xero_id, items={"Items": [item_data]}
            )
            time.sleep(SLEEP_TIME)
            logger.info(f"Updated stock item {stock_item.id} in Xero")
            return True

        # Still no xero_id → create
        resp = api.create_items(tenant_id, items={"Items": [item_data]})
        time.sleep(SLEEP_TIME)

        created = getattr(resp, "items", None) or getattr(resp, "Items", None) or []
        if not created:
            logger.error("Xero create_items returned empty response")
            return False

        xero_item = created[0]
        stock_item.xero_id = xero_item.item_id
        stock_item.xero_last_modified = timezone.now()
        stock_item.save(update_fields=["xero_id", "xero_last_modified"])
        logger.info(
            f"Created stock item {stock_item.id} in Xero with ID {stock_item.xero_id}"
        )
        return True

    except Exception as e:
        msg = str(e)

        # 3) Valid fallback: if error is "already exists" by Code, link and update
        # Note: this should be rare due to the initial lookup by Code above
        if "already exists" in msg and "Code" in msg:
            logger.warning(
                f"Create failed due to duplicate Code. Attempting link+update for {stock_item.item_code}"
            )
            existing = get_xero_item_by_code(api, tenant_id, stock_item.item_code)
            if not existing:
                logger.error(
                    "Duplicate reported, but item not found by Code — aborting"
                )
                return False

            stock_item.xero_id = existing.item_id
            stock_item.xero_last_modified = timezone.now()
            stock_item.save(update_fields=["xero_id", "xero_last_modified"])

            try:
                item_data["ItemID"] = stock_item.xero_id
                api.update_item(
                    tenant_id, item_id=stock_item.xero_id, items={"Items": [item_data]}
                )
                time.sleep(SLEEP_TIME)
                logger.info(
                    f"Recovered by linking and updating stock item {stock_item.id} -> Xero {stock_item.xero_id}"
                )
                return True
            except Exception as e2:
                logger.error(f"Failed to update after linking by Code: {e2}")
                persist_app_error(
                    e2,
                    additional_context={
                        "stock_id": str(stock_item.id),
                        "operation": "sync_stock_to_xero_update_after_duplicate",
                        "item_code": stock_item.item_code,
                    },
                )
                return False

        # Other errors: log and persist
        logger.error(f"Failed to sync stock item {stock_item.id} to Xero: {msg}")
        persist_app_error(
            e,
            additional_context={
                "stock_id": str(stock_item.id),
                "operation": "sync_stock_to_xero",
                "item_code": stock_item.item_code,
                "description": stock_item.description,
            },
        )
        return False


def sync_all_local_stock_to_xero(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Sync all local stock items that don't have xero_id to Xero.

    Args:
        limit: Optional limit on number of items to sync

    Returns:
        Dict with sync results
    """
    logger.info("Starting sync of local stock items to Xero")

    # Get stock items that need syncing (no xero_id and active)
    queryset = Stock.objects.filter(xero_id__isnull=True, is_active=True).order_by(
        "date"
    )

    if limit:
        queryset = queryset[:limit]

    total_items = queryset.count()
    synced_count = 0
    failed_count = 0
    failed_items = []

    logger.info(f"Found {total_items} stock items to sync to Xero")

    for stock_item in queryset:
        try:
            if sync_stock_to_xero(stock_item):
                synced_count += 1
                logger.info(f"Successfully synced stock item {stock_item.id}")
            else:
                failed_count += 1
                failed_items.append(
                    {
                        "id": str(stock_item.id),
                        "description": stock_item.description,
                        "reason": "Validation failed or API error",
                    }
                )
                logger.warning(f"Failed to sync stock item {stock_item.id}")
        except Exception as e:
            failed_count += 1
            failed_items.append(
                {
                    "id": str(stock_item.id),
                    "description": stock_item.description,
                    "reason": str(e),
                }
            )
            logger.error(f"Exception syncing stock item {stock_item.id}: {str(e)}")
            persist_app_error(e, additional_context={"stock_id": str(stock_item.id)})

    result = {
        "total_items": total_items,
        "synced_count": synced_count,
        "failed_count": failed_count,
        "failed_items": failed_items,
        "success_rate": (synced_count / total_items * 100) if total_items > 0 else 0,
    }

    logger.info(
        f"Completed stock sync: {synced_count}/{total_items} successful ({result['success_rate']:.1f}%)"
    )

    return result


def update_stock_item_codes():
    """
    Update item_code for existing stock items that don't have one or have invalid ones.
    This is a utility function to fix existing data.
    """
    logger.info("Starting update of missing/invalid item codes for stock items")

    # Find items with missing codes OR codes that are too long (>30 chars)
    stock_items = Stock.objects.filter(
        models.Q(item_code__isnull=True)
        | models.Q(item_code="")
        | models.Q(item_code__regex=r"^.{31,}$"),  # More than 30 characters
        is_active=True,
    )

    updated_count = 0

    for stock_item in stock_items:
        try:
            old_code = stock_item.item_code
            new_code = generate_item_code(stock_item)

            # Only update if the new code is different and valid
            if new_code != old_code and len(new_code) <= 30:
                stock_item.item_code = new_code
                stock_item.save(update_fields=["item_code"])
                updated_count += 1
                logger.info(
                    f"Updated stock {stock_item.id} item_code: '{old_code}' -> '{new_code}'"
                )
            elif len(new_code) > 30:
                logger.warning(
                    f"Generated code too long for stock {stock_item.id}: '{new_code}' ({len(new_code)} chars)"
                )

        except Exception as e:
            logger.error(
                f"Failed to update item_code for stock {stock_item.id}: {str(e)}"
            )
            persist_app_error(e, additional_context={"stock_id": str(stock_item.id)})

    logger.info(f"Updated item_code for {updated_count} stock items")
    return updated_count


def fix_long_item_codes():
    """
    Specifically fix item codes that are too long for Xero (>30 characters).
    """
    logger.info("Starting fix of long item codes for stock items")

    # Find items with codes longer than 30 characters
    long_code_items = Stock.objects.filter(
        item_code__regex=r"^.{31,}$", is_active=True  # More than 30 characters
    )

    fixed_count = 0

    for stock_item in long_code_items:
        try:
            old_code = stock_item.item_code

            # If it's a stock-{uuid} pattern, shorten it
            if old_code and old_code.startswith("stock-"):
                # Extract UUID and shorten
                uuid_part = old_code.replace("stock-", "")[:8]
                new_code = f"STK-{uuid_part}"
            else:
                # Use the standard generation logic
                new_code = generate_item_code(stock_item)

            # Ensure it's not too long
            if len(new_code) > 30:
                # Truncate if still too long
                new_code = new_code[:30]

            stock_item.item_code = new_code
            stock_item.save(update_fields=["item_code"])
            fixed_count += 1
            logger.info(
                f"Fixed long item_code for stock {stock_item.id}: '{old_code}' -> '{new_code}'"
            )

        except Exception as e:
            logger.error(
                f"Failed to fix long item_code for stock {stock_item.id}: {str(e)}"
            )
            persist_app_error(e, additional_context={"stock_id": str(stock_item.id)})

    logger.info(f"Fixed {fixed_count} long item codes")
    return fixed_count
