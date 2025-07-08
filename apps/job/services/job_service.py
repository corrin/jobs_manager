import logging

from django.db import transaction

from apps.accounts.models import Staff
from apps.job.models import Job

logger = logging.getLogger(__name__)


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
