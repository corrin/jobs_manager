import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.job.services.job_service import recalculate_job_invoicing_state

from .models import Invoice

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Invoice)
def invoice_post_save_recalc_job(sender, instance: Invoice, **kwargs):
    # If save comes from loaddata/fixtures, we do an early return to avoid unexpected side effects
    if kwargs.get("raw"):
        return

    def _recalc():
        recalculate_job_invoicing_state(instance.job.id)

    transaction.on_commit(_recalc)


@receiver(post_delete, sender=Invoice)
def invoice_post_delete_recalc_job(sender, instance: Invoice, **kwargs):
    def _recalc():
        recalculate_job_invoicing_state(instance.job.id)

    logger.info(
        f"Scheduling job recalculation for job {instance.job.id} after invoice deletion"
    )
    transaction.on_commit(_recalc)
