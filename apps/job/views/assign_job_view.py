import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.services.job_service import JobStaffService

logger = logging.getLogger(__name__)


class AssignJobView(APIView):
    """API Endpoint for activities related to job assignment"""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            job_id = request.data.get("job_id", None)

            if not job_id:
                return Response(
                    {
                        "success": False,
                        "error": "No job ID was provided. Please try again or contact an administrator if the problem persists.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            staff_id = request.data.get("staff_id", None)

            if not staff_id:
                return Response(
                    {
                        "success": False,
                        "error": "No staff ID was provided. Please try again or contact an administrator if the problem persists.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            success, error = JobStaffService.assign_staff_to_job(job_id, staff_id)

            if success:
                return Response(
                    {"success": True, "message": "Job assigned to staff successfully."},
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"success": False, "error": error}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, *args, **kwargs):
        try:
            job_id = request.data.get("job_id", None)

            if not job_id:
                return Response(
                    {
                        "success": False,
                        "error": "No job ID was provided. Please try again or contact an administrator if the problem persists.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            staff_id = request.data.get("staff_id", None)

            if not staff_id:
                return Response(
                    {
                        "success": False,
                        "error": "No staff ID was provided. Please try again or contact an administrator if the problem persists.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            success, error = JobStaffService.remove_staff_from_job(job_id, staff_id)

            if success:
                return Response(
                    {"success": True, "message": "Job assigned to staff successfully."},
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"success": False, "error": error}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
