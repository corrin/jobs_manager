import logging
from django.core.paginator import Paginator
from django.db import transaction

from apps.accounting.models import Invoice, InvoiceLineItem
from apps.workflow.models import XeroAccount

logger = logging.getLogger(__name__)


def sync_line_items_for_existing_invoices(batch_size=1000):
    # Get all invoices and paginate through them in batches
    paginator = Paginator(Invoice.objects.all(), batch_size)

    for page_number in paginator.page_range:
        logger.info(f"Processing batch {page_number}")
        with transaction.atomic():
            for invoice in paginator.page(page_number).object_list:
                raw_json = invoice.raw_json  # Extract raw JSON data from the invoice
                line_items_data = raw_json.get(
                    "line_items", []
                )  # Line items from the raw JSON

                for line_item_data in line_items_data:
                    description = line_item_data.get("description")
                    quantity = line_item_data.get("quantity", 1)
                    unit_price = line_item_data.get("unit_price")
                    account_code = line_item_data.get("account_code")

                    # Find the associated account
                    account = XeroAccount.objects.filter(
                        account_code=account_code
                    ).first()

                    # Update or create the line item
                    InvoiceLineItem.objects.update_or_create(
                        invoice=invoice,
                        description=description,
                        defaults={
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "account": account,
                        },
                    )
        logger.info(f"Batch {page_number} processed.")

    logger.info("Line item sync for existing invoices completed!")
