import logging

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from workflow.models import CompanyDefaults

from job.models import Job, JobPricing, AdjustmentEntry, MaterialEntry

from timesheet.models import TimeEntry

from accounts.models import Staff

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
            pricing_type="estimate",
        )
        TimeEntry.objects.create(
            part=estimate_pricing.get_default_part(),
            wage_rate=company_defaults.wage_rate,
            charge_out_rate=company_defaults.charge_out_rate,
        )

        # Create new pricing for "quote"
        quote_pricing = JobPricing.objects.create(
            job=job,
            pricing_type="quote",
        )
        AdjustmentEntry.objects.create(
            part=quote_pricing.get_default_part(),
            cost_adjustment=company_defaults.time_markup,
            price_adjustment=company_defaults.charge_out_rate
            * company_defaults.time_markup,
        )

        # Create new pricing for "reality"
        reality_pricing = JobPricing.objects.create(
            job=job,
            pricing_type="reality",
        )
        MaterialEntry.objects.create(
            part=reality_pricing.get_default_part(),
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

    # Define pricing types to reduce redundancy
    pricing_types = [
        "latest_estimate_pricing",
        "latest_quote_pricing",
        "latest_reality_pricing",
    ]

    # Prefetch list to store all prefetch operations
    prefetch_list = []

    # Loop through each pricing type to create Prefetch objects for pricing entries
    for pt in pricing_types:
        # Prefetch time_entries with related staff through parts
        prefetch_list.append(
            Prefetch(
                f"{pt}__parts__time_entries",
                queryset=TimeEntry.objects.select_related("staff"),
            )
        )
        # Prefetch material_entries through parts
        prefetch_list.append(
            Prefetch(f"{pt}__parts__material_entries", queryset=MaterialEntry.objects.all())
        )
        # Prefetch adjustment_entries through parts
        prefetch_list.append(
            Prefetch(
                f"{pt}__parts__adjustment_entries", queryset=AdjustmentEntry.objects.all()
            )
        )

    # Get the job with the relevant prefetch operations for each pricing type
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


# Utility to fetch the latest pricing per type
def get_latest_job_pricings(job):
    """Fetches the latest revision of each pricing type for the given job."""
    return {
        "estimate_pricing": job.latest_estimate_pricing,
        "quote_pricing": job.latest_quote_pricing,
        "reality_pricing": job.latest_reality_pricing,
    }


def get_paid_complete_jobs():
    """Fetches the jobs that are both completed and paid."""
    return ( 
        Job.objects.filter(status="completed", paid=True)
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
                job.save(update_fields=['status'])
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
