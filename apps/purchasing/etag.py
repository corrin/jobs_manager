"""Helper utilities for Purchase Order ETag handling."""

from __future__ import annotations

from typing import Optional

from apps.purchasing.models import PurchaseOrder


def normalize_etag(etag: Optional[str]) -> Optional[str]:
    """Normalize an ETag header value for comparison."""
    if not etag:
        return None
    val = etag.strip()
    if val.startswith("W/"):
        val = val[2:].strip()
    if len(val) >= 2 and (
        (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")
    ):
        val = val[1:-1]
    return val or None


def generate_po_etag(po: PurchaseOrder) -> str:
    """Generate a weak ETag for a purchase order based on last modification time."""
    try:
        ts_ms = int(po.updated_at.timestamp() * 1000)
    except Exception:
        ts_ms = 0
    return f'W/"po:{po.id}:{ts_ms}"'
