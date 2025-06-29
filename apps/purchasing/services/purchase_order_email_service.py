import logging
from urllib.parse import quote

from apps.purchasing.models import PurchaseOrder

logger = logging.getLogger(__name__)


def create_purchase_order_email(purchase_order: PurchaseOrder) -> dict:
    """
    Create and email for a purchase order.

    Args:
        purchase_order: The PurchaseOrder instance

    Returns:
        dict: a Dictionary containing the mailto URL and other email related data
    """
    if not purchase_order.supplier or not purchase_order.supplier.email:
        raise ValueError("Purchase order supplier has no email")

    email = purchase_order.supplier.email

    subject = f"Purchase Order {purchase_order.po_number}"
    body = (
        f"Hi,\n\n"
        f"Please find attached Purchase Order #{purchase_order.po_number}.\n\n"
        f"If you have any questions about this order, please reply to this e-mail.\n\n"
        f"Thanks,\nMorris Sheetmetals Ltd."
    )

    mailto_url = f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"

    logger.info(
        f"Email prepared for purchase order {purchase_order.po_number}")

    return {
        "success": True,
        "mailto_url": mailto_url,
        "email": email,
        "subject": subject,
        "body": body,
    }
