import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.serializers import AssignJobResponseSerializer, AssignJobSerializer
from apps.job.services.job_service import JobStaffService

logger = logging.getLogger(__name__)


class AssignJobView(APIView):
    """API Endpoint for activities related to job assignment"""

    permission_classes = [IsAuthenticated]
    serializer_class = AssignJobResponseSerializer

    def get_serializer_class(self):
        """Return the serializer class for documentation"""
        if hasattr(self, "action") and self.action in ["post", "delete"]:
            return AssignJobSerializer
        return AssignJobResponseSerializer

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance"""
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    @extend_schema(
        request=AssignJobSerializer,
        responses={status.HTTP_200_OK: AssignJobResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        try:
            # Validate request data
            request_serializer = AssignJobSerializer(data=request.data)
            if not request_serializer.is_valid():
                response_serializer = AssignJobResponseSerializer(
                    data={"success": False, "error": "Invalid request data"}
                )
                response_serializer.is_valid(raise_exception=True)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job_id = request_serializer.validated_data["job_id"]
            staff_id = request_serializer.validated_data["staff_id"]

            success, error = JobStaffService.assign_staff_to_job(job_id, staff_id)

            if success:
                response_serializer = AssignJobResponseSerializer(
                    data={
                        "success": True,
                        "message": "Job assigned to staff successfully.",
                    }
                )
                response_serializer.is_valid(raise_exception=True)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_200_OK,
                )

            response_serializer = AssignJobResponseSerializer(
                data={"success": False, "error": error}
            )
            response_serializer.is_valid(raise_exception=True)
            return Response(
                response_serializer.data, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            response_serializer = AssignJobResponseSerializer(
                data={"success": False, "error": str(e)}
            )
            response_serializer.is_valid(raise_exception=True)
            return Response(
                response_serializer.data,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        request=AssignJobSerializer,
        responses={status.HTTP_200_OK: AssignJobResponseSerializer},
    )
    def delete(self, request, job_id):
        try:
            # Validate request data
            request_serializer = AssignJobSerializer(data=request.data)
            if not request_serializer.is_valid():
                logger.error(f"Invalid request data: {request_serializer.errors}")
                response_serializer = AssignJobResponseSerializer(
                    data={"success": False, "error": "Invalid request data"}
                )
                response_serializer.is_valid(raise_exception=True)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            staff_id = request_serializer.validated_data["staff_id"]

            success, error = JobStaffService.remove_staff_from_job(job_id, staff_id)

            if success:
                response_serializer = AssignJobResponseSerializer(
                    data={
                        "success": True,
                        "message": "Staff removed from job successfully.",
                    }
                )
                response_serializer.is_valid(raise_exception=True)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_200_OK,
                )

            response_serializer = AssignJobResponseSerializer(
                data={"success": False, "error": error}
            )
            response_serializer.is_valid(raise_exception=True)
            return Response(
                response_serializer.data, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error removing staff from job: {e}")
            response_serializer = AssignJobResponseSerializer(
                data={"success": False, "error": str(e)}
            )
            response_serializer.is_valid(raise_exception=True)
            return Response(
                response_serializer.data,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
