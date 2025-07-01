import logging

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from apps.accounts.models import Staff
from apps.job.models import AdjustmentEntry, Job, JobPricing, MaterialEntry
from apps.timesheet.models import TimeEntry
from apps.workflow.models import CompanyDefaults

logger = logging.getLogger(__name__)


def archive_and_reset_job_pricing(job_id):
    """Archives current pricing and resets to defaults based on company defaults."""
    job = Job.objects.get(id=job_id)

    # Fetch company defaults (assuming only one instance exists)
    company_defaults = CompanyDefaults.objects.first()
    if not company_defaults:
        raise ValueError("Company defaults are not configured.")

    with transaction.atomic():
        # Archive current pricing by marking them as historical
        current_pricings = JobPricing.objects.filter(job=job, is_historical=False)
        for pricing in current_pricings:
            pricing.is_historical = True
            pricing.save()
            # Add to the archived_pricings relationship
            job.archived_pricings.add(pricing)

        # Create new pricing for "estimate"
        estimate_pricing = JobPricing.objects.create(
            job=job,
            pricing_stage="estimate",
        )
        estimate_pricing.time_entries.create(
            wage_rate=company_defaults.wage_rate,
            charge_out_rate=company_defaults.charge_out_rate,
        )

        # Create new pricing for "quote"
        quote_pricing = JobPricing.objects.create(
            job=job,
            pricing_stage="quote",
        )
        quote_pricing.adjustment_entries.create(
            cost_adjustment=company_defaults.time_markup,
            price_adjustment=company_defaults.charge_out_rate
            * company_defaults.time_markup,
        )

        # Create new pricing for "reality"
        reality_pricing = JobPricing.objects.create(
            job=job,
            pricing_stage="reality",
        )
        reality_pricing.material_entries.create(
            unit_cost=company_defaults.wage_rate,
            unit_revenue=company_defaults.charge_out_rate,
        )

        # Save references to the job
        job.latest_estimate_pricing = estimate_pricing
        job.latest_quote_pricing = quote_pricing
        job.latest_reality_pricing = reality_pricing
        job.save()


def get_job_with_pricings(job_id):
    """Fetches a Job object with all relevant latest JobPricing data,
    including time, material, and adjustment entries."""

    # Define pricing stages to reduce redundancy
    pricing_stages = [
        "latest_estimate_pricing",
        "latest_quote_pricing",
        "latest_reality_pricing",
    ]

    # Prefetch list to store all prefetch operations
    prefetch_list = []

    # Loop through each pricing stage to create Prefetch objects for pricing entries
    for stage in pricing_stages:
        # Prefetch time_entries with related staff
        prefetch_list.append(
            Prefetch(
                f"{stage}__time_entries",
                queryset=TimeEntry.objects.select_related("staff"),
            )
        )
        # Prefetch material_entries
        prefetch_list.append(
            Prefetch(f"{stage}__material_entries", queryset=MaterialEntry.objects.all())
        )
        # Prefetch adjustment_entries
        prefetch_list.append(
            Prefetch(
                f"{stage}__adjustment_entries", queryset=AdjustmentEntry.objects.all()
            )
        )

    # Get the job with the relevant prefetch operations for each pricing stage
    job = get_object_or_404(
        Job.objects.select_related("client").prefetch_related(*prefetch_list),
        id=job_id,
    )

    return job


def get_historical_job_pricings(job):
    """Fetch all historical (archived) revisions for the job."""
    # Fetch all archived pricings for the given job
    historical_pricings = job.archived_pricings.all().order_by("-created_at")
    return list(historical_pricings)


# Utility to fetch the latest pricing per stage
def get_latest_job_pricings(job):
    """Fetches the latest revision of each pricing stage for the given job."""
    return {
        "estimate_pricing": job.latest_estimate_pricing,
        "quote_pricing": job.latest_quote_pricing,
        "reality_pricing": job.latest_reality_pricing,
    }


def get_paid_complete_jobs():
    """Fetches the jobs that are both completed and paid."""
    return (
        Job.objects.filter(status__in=["completed", "recently_completed"], paid=True)
        .select_related("client")
        .order_by("-updated_at")
    )


def archive_complete_jobs(job_ids):
    """Archives the jobs on the provided list by changing their statuses"""
    archived_count = 0
    errors = []

    with transaction.atomic():
        for jid in job_ids:
            try:
                job = Job.objects.get(id=jid)
                job.status = "archived"
                job.save(update_fields=["status"])
                archived_count += 1
                logger.info(f"Job {jid} successfully archived")
            except Job.DoesNotExist:
                errors.append(f"Job with id {jid} not found")
            except Exception as e:
                errors.append(f"Failed to archive job {jid}: {str(e)}")
                logger.error(f"Error archiving job {jid}: {str(e)}")

    return errors, archived_count


class JobStaffService:
    @staticmethod
    def assign_staff_to_job(job_id, staff_id):
        """Assign a staff member to a job"""
        try:
            job = Job.objects.get(id=job_id)
            staff = Staff.objects.get(id=staff_id)

            if staff not in job.people.all():
                job.people.add(staff)

            return True, None
        except Job.DoesNotExist:
            return False, "Job not found"
        except Staff.DoesNotExist:
            return False, "Staff member not found"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def remove_staff_from_job(job_id, staff_id):
        """Remove a staff member from a job"""
        try:
            job = Job.objects.get(id=job_id)
            staff = Staff.objects.get(id=staff_id)

            if staff in job.people.all():
                job.people.remove(staff)

            return True, None
        except Job.DoesNotExist:
            return False, "Job not found"
        except Staff.DoesNotExist:
            return False, "Staff member not found"
        except Exception as e:
            raise e
