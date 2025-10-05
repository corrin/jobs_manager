import logging
import traceback

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.job.services.job_service import recalculate_job_invoicing_state

from .models import Invoice

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Invoice)
def invoice_post_save_recalc_job(sender, instance: Invoice, **kwargs):
    # REDUNDANT: Log ALL callers so we can identify them before removing this signal
    stack = traceback.extract_stack()
    caller_info = f"{stack[-2].filename}:{stack[-2].lineno} in {stack[-2].name}"
    logger.error(
        f"REDUNDANT SIGNAL invoice_post_save_recalc_job CALLED from {caller_info}"
    )

    # If save comes from loaddata/fixtures, we do an early return to avoid unexpected side effects
    if kwargs.get("raw"):
        return

    # Invoices from Xero sync may not have a job - no recalculation needed
    if not instance.job:
        return

    def _recalc():
        recalculate_job_invoicing_state(instance.job.id)

    transaction.on_commit(_recalc)


@receiver(post_delete, sender=Invoice)
def invoice_post_delete_recalc_job(sender, instance: Invoice, **kwargs):
    # REDUNDANT: Log ALL callers so we can identify them before removing this signal
    stack = traceback.extract_stack()
    caller_info = f"{stack[-2].filename}:{stack[-2].lineno} in {stack[-2].name}"
    logger.error(
        f"REDUNDANT SIGNAL invoice_post_delete_recalc_job CALLED from {caller_info}"
    )

    # Invoices from Xero sync may not have a job - no recalculation needed
    if not instance.job:
        return

    def _recalc():
        recalculate_job_invoicing_state(instance.job.id)

    transaction.on_commit(_recalc)
