"""
Job Costing REST Views

REST views for the Job costing system to expose CostSet data
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.mixins import JobLookupMixin
from apps.job.models import Job
from apps.job.serializers import CostSetSerializer

logger = logging.getLogger(__name__)


class JobCostSetView(JobLookupMixin, APIView):
    lookup_url_kwarg = "pk"  # Match the URL parameter name
    """
    Retrieve the latest CostSet for a specific job and kind.

    GET /jobs/<pk>/cost_sets/<kind>/

    Returns the latest CostSet of the specified kind (estimate|quote|actual)
    for the given job, or 404 if not found.
    """

    def get(self, request, pk, kind):
        """
        Get the latest CostSet for a job by kind.

        Args:
            pk: Job primary key (UUID)
            kind: CostSet kind ('estimate', 'quote', or 'actual')

        Returns:
            Response: Serialized CostSet data or 404
        """
        # Validate kind parameter
        valid_kinds = ["estimate", "quote", "actual"]
        if kind not in valid_kinds:
            return Response(
                {"error": f"Invalid kind. Must be one of: {', '.join(valid_kinds)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the job
        job, error_response = self.get_job_or_404_response(error_format="legacy")
        if error_response:
            return error_response

        # Get the latest CostSet using the job's helper method
        cost_set = job.get_latest(kind)

        if cost_set is None:
            return Response(
                {"error": f"No {kind} cost set found for this job"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Serialize and return the cost set
        serializer = CostSetSerializer(cost_set)
        return Response(serializer.data, status=status.HTTP_200_OK)
