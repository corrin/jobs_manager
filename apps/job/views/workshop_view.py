from logging import getLogger

from rest_framework.generics import ListAPIView

from apps.job.models import Job
from apps.job.serializers.kanban_serializer import WorkshopJobSerializer

logger = getLogger(__name__)


class WorkshopKanbanView(ListAPIView):
    serializer_class = WorkshopJobSerializer

    def get_queryset(self):
        """Retrieve jobs for the workshop kanban view."""
        staff = self.request.user
        logger.info(f"Fetching in-progress jobs for staff ID: {staff.id}")
        jobs = Job.objects.filter(people__id=staff.id, status__in=["in_progress"])
        logger.info(f"Retrieved {jobs.count()} jobs for staff ID: {staff.id}")

        return [
            {
                "id": job.id,
                "name": job.name,
                "description": job.description,
                "job_number": job.job_number,
                "client_name": job.client.name,
                "contact_person": job.contact.name if job.contact else None,
                "people": [
                    {
                        "id": staff.id,
                        "display_name": f"{staff.preferred_name or staff.first_name} {staff.last_name}",
                        "icon_url": staff.icon.url if staff.icon else None,
                    }
                    for staff in job.people.all()
                ],
            }
            for job in jobs
        ]
