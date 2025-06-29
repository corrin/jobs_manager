"""
Service layer for Kanban functionality.
Handles all business logic related to job management in the Kanban board.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from django.db import transaction
from django.db.models import Max, Q, QuerySet
from django.http import HttpRequest

from apps.job.models import Job
from apps.job.services.kanban_categorization_service import KanbanCategorizationService

logger = logging.getLogger(__name__)


class KanbanService:
    """Service class for Kanban business logic."""

    @staticmethod
    def get_jobs_by_status(
        status: str, search_terms: Optional[List[str]] = None, limit: int = 200
    ) -> QuerySet[Job]:
        """
        Get jobs filtered by status and optional search terms.

        Args:
            status: Job status to filter by
            search_terms: List of search terms to filter jobs
            limit: Maximum number of jobs to return

        Returns:
            QuerySet of filtered jobs
        """
        jobs_query = Job.objects.filter(status=status)

        if search_terms:
            query = Q()
            for term in search_terms:
                term_query = (
                    Q(name__icontains=term)
                    | Q(description__icontains=term)
                    | Q(client__name__icontains=term)
                    | Q(contact_person__icontains=term)
                    | Q(created_by__email__icontains=term)
                )
                query &= term_query
            jobs_query = jobs_query.filter(query)

        jobs = jobs_query.order_by("-priority", "-created_at")

        # Apply different limits based on status
        match status:
            case "archived":
                return jobs[:100]
            case _:
                return jobs[:limit]

    @staticmethod
    def get_all_active_jobs() -> QuerySet[Job]:
        """Get all active (non-archived) jobs, filtered for kanban display, ordered by priority only."""
        # Get non-archived jobs and filter out special jobs for kanban
        active_jobs = Job.objects.exclude(status="archived").order_by("-priority")
        return KanbanService.filter_kanban_jobs(active_jobs)

    @staticmethod
    def get_archived_jobs(limit: int = 50) -> QuerySet[Job]:
        """Get archived jobs with limit."""
        return Job.objects.filter(status="archived").order_by("-created_at")[:limit]

    @staticmethod
    def get_status_choices() -> Dict[str, Any]:
        """Get available status choices and tooltips using new categorization."""
        categorization_service = KanbanCategorizationService

        # Get all kanban columns instead of individual statuses
        columns = categorization_service.get_all_columns()

        # Create status choices based on columns (for backward compatibility)
        status_choices = {}
        status_tooltips = {}

        for column in columns:
            # Use column as the main "status" for the kanban view
            status_choices[column.column_id] = column.column_title

            # Create tooltip that shows sub-categories
            sub_cat_labels = [sub_cat.badge_label for sub_cat in column.sub_categories]
            status_tooltips[column.column_id] = f"Includes: {', '.join(sub_cat_labels)}"

        return {"statuses": status_choices, "tooltips": status_tooltips}

    @staticmethod
    def serialize_job_for_api(job: Job, request: HttpRequest) -> Dict[str, Any]:
        """
        Serialize a job object for API response.

        Args:
            job: Job instance to serialize
            request: HTTP request for building absolute URIs

        Returns:
            Dictionary representation of the job
        """
        return {
            "id": job.id,
            "name": job.name,
            "description": job.description,
            "job_number": job.job_number,
            "client_name": job.client.name if job.client else "",
            "contact_person": job.contact_person,
            "people": [
                {
                    "id": staff.id,
                    "display_name": staff.get_display_full_name(),
                    "icon": (
                        request.build_absolute_uri(staff.icon.url)
                        if staff.icon
                        else None
                    ),
                }
                for staff in job.people.all()
            ],
            "status": job.get_status_display(),
            "status_key": job.status,
            "paid": job.paid,
            "created_by_id": job.created_by.id if job.created_by else None,
            "created_at": (
                job.created_at.strftime("%d/%m/%Y") if job.created_at else None
            ),
            "priority": job.priority,
        }

    @staticmethod
    def update_job_status(job_id: UUID, new_status: str) -> bool:
        """
        Update job status.

        Args:
            job_id: UUID of the job to update
            new_status: New status value

        Returns:
            True if successful, False otherwise

        Raises:
            Job.DoesNotExist: If job not found
        """
        try:
            job = Job.objects.get(pk=job_id)
            job.status = new_status
            job.save(update_fields=["status"])
            return True
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found for status update")
            raise

    @staticmethod
    def get_adjacent_priorities(
        before_id: Optional[str], after_id: Optional[str]
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Get priorities of adjacent jobs.

        Args:
            before_id: ID of job before the target position
            after_id: ID of job after the target position

        Returns:
            Tuple of (before_priority, after_priority)

        Raises:
            Job.DoesNotExist: If referenced job not found
        """
        before_prio = None
        after_prio = None

        if before_id:
            before_prio = Job.objects.get(pk=before_id).priority
        if after_id:
            after_prio = Job.objects.get(pk=after_id).priority

        return before_prio, after_prio

    @staticmethod
    def rebalance_column(status: str) -> None:
        """
        Rebalance priorities in a status column.

        Args:
            status: Status column to rebalance
        """
        increment = Job.PRIORITY_INCREMENT
        jobs = list(Job.objects.filter(status=status).order_by("-priority"))

        with transaction.atomic():
            for index, job in enumerate(jobs, start=1):
                job.priority = index * increment
                job.save(update_fields=["priority"])

    @staticmethod
    def calculate_priority(
        before_prio: Optional[int], after_prio: Optional[int], status: str
    ) -> int:
        """
        Calculate new priority for job positioning.

        Args:
            before_prio: Priority of job before target position
            after_prio: Priority of job after target position
            status: Status column for the job

        Returns:
            Calculated priority value
        """
        increment = Job.PRIORITY_INCREMENT

        match (before_prio, after_prio):
            case (None, None):
                # No adjacent jobs; place at end
                max_prio = (
                    Job.objects.filter(status=status).aggregate(Max("priority"))[
                        "priority__max"
                    ]
                    or 0
                )
                return max_prio + increment

            case (None, after) if after is not None:
                # Insert at top: place just above the 'after' job
                new_prio = after - increment
                if new_prio <= 0:
                    KanbanService.rebalance_column(status)
                    # Re-fetch after_prio after rebalance
                    after = Job.objects.get(priority=after, status=status).priority
                    return after - increment
                return new_prio

            case (before, None) if before is not None:
                # Insert at bottom: place just below the 'before' job
                return before + increment

            case (before, after) if before is not None and after is not None:
                # Internal insertion: try to take the average
                gap = after - before
                if gap > 1:
                    return (before + after) // 2
                # Gap too small → rebalance first, then recompute
                KanbanService.rebalance_column(status)
                before = Job.objects.get(priority=before, status=status).priority
                after = Job.objects.get(priority=after, status=status).priority
                return (before + after) // 2

            case _:
                # Fallback: push to end if anything unexpected happens
                max_prio = (
                    Job.objects.filter(status=status).aggregate(Max("priority"))[
                        "priority__max"
                    ]
                    or 0
                )
                return max_prio + increment

    @staticmethod
    def reorder_job(
        job_id: UUID,
        before_id: Optional[str] = None,
        after_id: Optional[str] = None,
        new_status: Optional[str] = None,
    ) -> bool:
        """
        Reorder a job within or between columns.

        Args:
            job_id: UUID of job to reorder
            before_id: ID of job before target position
            after_id: ID of job after target position
            new_status: New status if moving between columns

        Returns:
            True if successful

        Raises:
            Job.DoesNotExist: If job not found
        """
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found for reordering")
            raise

        try:
            before_prio, after_prio = KanbanService.get_adjacent_priorities(
                before_id, after_id
            )
        except Job.DoesNotExist:
            logger.error(f"Adjacent job not found for reordering job {job_id}")
            raise

        # Determine target status for priority calculation
        target_status = new_status if new_status else job.status

        # Calculate new priority
        new_priority = KanbanService.calculate_priority(
            before_prio, after_prio, target_status
        )
        job.priority = new_priority

        # Update status if needed
        old_status = job.status
        update_fields = ["priority"]

        if new_status and new_status != old_status:
            job.status = new_status
            update_fields.insert(0, "status")

        job.save(update_fields=update_fields)
        return True

    @staticmethod
    def perform_advanced_search(filters: Dict[str, Any]) -> QuerySet[Job]:
        """
        Perform advanced search with multiple filters.

        Args:
            filters: Dictionary of search filters

        Returns:
            QuerySet of filtered jobs
        """
        jobs_query = Job.objects.all()

        # Apply filters with early returns for invalid data
        if number := filters.get("job_number", "").strip():
            jobs_query = jobs_query.filter(job_number=number)

        if name := filters.get("name", "").strip():
            jobs_query = jobs_query.filter(name__icontains=name)

        if description := filters.get("description", "").strip():
            jobs_query = jobs_query.filter(description__icontains=description)

        if client_name := filters.get("client_name", "").strip():
            jobs_query = jobs_query.filter(client__name__icontains=client_name)

        if contact_person := filters.get("contact_person", "").strip():
            jobs_query = jobs_query.filter(contact_person__icontains=contact_person)

        if created_by := filters.get("created_by", "").strip():
            jobs_query = jobs_query.filter(events__staff=created_by)

        if created_after := filters.get("created_after", "").strip():
            jobs_query = jobs_query.filter(created_at__gte=created_after)

        if created_before := filters.get("created_before", "").strip():
            jobs_query = jobs_query.filter(created_at__lte=created_before)

        if statuses := filters.get("status", []):
            jobs_query = jobs_query.filter(status__in=statuses)

        # Handle paid filter with match-case
        paid_filter = filters.get("paid", "")
        match paid_filter:
            case "true":
                jobs_query = jobs_query.filter(paid=True)
            case "false":
                jobs_query = jobs_query.filter(paid=False)

        return jobs_query.order_by("-created_at")

    @staticmethod
    def get_jobs_by_kanban_column(
        column_id: str, max_jobs: int = 50, search_term: str = ""
    ) -> Dict[str, Any]:
        """Get jobs by kanban column using new categorization system."""
        categorization_service = KanbanCategorizationService

        # Early return for invalid column
        if column_id not in [
            col.column_id for col in categorization_service.get_all_columns()
        ]:
            return {
                "success": False,
                "error": f"Invalid column: {column_id}",
                "jobs": [],
                "total": 0,
                "filtered_count": 0,
            }

        try:
            # Get column information
            column = categorization_service.get_column_by_id(column_id)
            if not column:
                return {
                    "success": False,
                    "error": "Column not found",
                    "jobs": [],
                    "total": 0,
                    "filtered_count": 0,
                }

            # Get valid statuses for this column
            valid_statuses = [
                sub_cat.status_key for sub_cat in column.sub_categories
            ]  # Build base query and filter out 'special' jobs
            jobs_query = Job.objects.filter(status__in=valid_statuses).select_related(
                "client"
            )
            jobs_query = KanbanService.filter_kanban_jobs(jobs_query)

            # Apply search filter if provided
            if search_term:
                search_query = (
                    Q(name__icontains=search_term)
                    | Q(job_number__icontains=search_term)
                    | Q(description__icontains=search_term)
                    | Q(client__name__icontains=search_term)
                )
                jobs_query = jobs_query.filter(search_query)

            # Get total count
            total_count = jobs_query.count()

            # Apply limit and ordering
            jobs = jobs_query.order_by("-priority")[:max_jobs]

            # Format jobs with badge information
            formatted_jobs = []
            for job in jobs:
                # Get badge info for the actual job status
                badge_info = categorization_service.get_badge_info(job.status)

                job_data = {
                    "id": str(job.id),
                    "job_number": job.job_number,
                    "name": job.name,
                    "description": job.description or "",
                    "client_name": job.client.name if job.client else "No Client",
                    "contact_person": job.contact_person or "",
                    "people": [],  # This would need to be populated with assigned staff
                    "status": job.status,
                    "status_key": job.status,
                    "paid": job.paid,
                    "created_by_id": (
                        str(job.created_by_id) if job.created_by_id else None
                    ),
                    "created_at": (
                        job.created.isoformat() if hasattr(job, "created") else None
                    ),
                    "priority": job.priority,
                    # New badge information
                    "badge_label": badge_info["label"],
                    "badge_color": badge_info["color_class"],
                }
                formatted_jobs.append(job_data)

            return {
                "success": True,
                "jobs": formatted_jobs,
                "total": total_count,
                "filtered_count": len(formatted_jobs),
            }

        except Exception as e:
            logger.error(f"Error getting jobs for column {column_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "jobs": [],
                "total": 0,
                "filtered_count": 0,
            }

    @staticmethod
    def filter_kanban_jobs(jobs_query):
        """
        Filter jobs for kanban display - excludes 'special' status

        Args:
            jobs_query: QuerySet of jobs to filter

        Returns:
            Filtered QuerySet excluding special jobs
        """
        return jobs_query.exclude(status="special")
