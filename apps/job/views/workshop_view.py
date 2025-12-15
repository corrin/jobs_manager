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
        qs = Job.objects.filter(people__id=staff.id, status__in=["in_progress"])
        logger.info(f"Retrieved {qs.count()} jobs for staff ID: {staff.id}")

        return qs
