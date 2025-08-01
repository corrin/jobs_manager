# This file is autogenerated by update_init.py script

from .xero_helpers import (
    clean_payload,
    convert_to_pascal_case,
    format_date,
    parse_xero_api_error_message,
)

# Conditional imports (only when Django is ready)
try:
    from django.apps import apps

    if apps.ready:
        from .xero_base_manager import XeroDocumentManager
        from .xero_invoice_manager import XeroInvoiceManager
        from .xero_po_manager import XeroPurchaseOrderManager
        from .xero_quote_manager import XeroQuoteManager
except (ImportError, RuntimeError):
    # Django not ready or circular import, skip conditional imports
    pass

__all__ = [
    "XeroDocumentManager",
    "XeroInvoiceManager",
    "XeroPurchaseOrderManager",
    "XeroQuoteManager",
    "clean_payload",
    "convert_to_pascal_case",
    "format_date",
    "parse_xero_api_error_message",
]
