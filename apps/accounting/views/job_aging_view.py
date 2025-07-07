from logging import getLogger

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounting.services import JobAgingService
from apps.workflow.services.error_persistence import persist_app_error

logger = getLogger(__name__)


class JobAgingAPIView(APIView):
    """API Endpoint to provide job aging data with financial and timing information"""

    def get(self, request, *args, **kwargs):
        """
        Get job aging data.
        
        Query Parameters:
            include_archived (bool): Whether to include archived jobs. Defaults to False.
        
        Returns:
            JSON response with job aging data structure
        """
        try:
            # Get query parameters
            include_archived_param = request.query_params.get("include_archived", "false")
            
            # Parse boolean parameter
            if include_archived_param.lower() in ("true", "1", "yes"):
                include_archived = True
            elif include_archived_param.lower() in ("false", "0", "no"):
                include_archived = False
            else:
                return Response(
                    {
                        "error": "Invalid value for 'include_archived' parameter. "
                        "Expected: true, false, 1, 0, yes, or no."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get job aging data from service
            job_aging_data = JobAgingService.get_job_aging_data(
                include_archived=include_archived
            )

            return Response(job_aging_data, status=status.HTTP_200_OK)
            
        except Exception as exc:
            logger.error(f"Job Aging API Error: {str(exc)}")
            persist_app_error(exc)
            return Response(
                {"error": f"Error obtaining job aging data: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )