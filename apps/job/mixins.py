"""
Job-related mixins for Django REST Framework views.
"""

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.job.models import Job


class JobLookupMixin(GenericAPIView):
    """
    Mixin that provides consistent job lookup functionality for REST views.

    Supports both UUID-based lookups (job_id) and job_number-based lookups.
    Provides consistent error responses following the existing API patterns.
    """

    queryset = Job.objects.all()
    lookup_field = "id"  # Default to UUID lookup
    lookup_url_kwarg = "job_id"  # Default URL parameter name

    def get_job_by_number(self, job_number):
        """
        Get job by job_number instead of UUID.
        Used for endpoints that use job_number in the business logic.
        """
        try:
            return Job.objects.get(job_number=job_number)
        except Job.DoesNotExist:
            return None

    def get_job_or_404_response(self, job_number=None, error_format="api"):
        """
        Get job or return appropriate 404 response.

        Args:
            job_number: If provided, lookup by job_number instead of URL param
            error_format: 'api' for new API format, 'legacy' for old format

        Returns:
            tuple: (job_instance, error_response)
            If job found: (job, None)
            If job not found: (None, Response)
        """
        if job_number:
            job = self.get_job_by_number(job_number)
        else:
            try:
                job = self.get_object()
            except:
                job = None

        if job is None:
            if error_format == "api":
                error_response = Response(
                    {
                        "success": False,
                        "error": "Job not found",
                        "code": "JOB_NOT_FOUND",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            else:  # legacy format
                error_response = Response(
                    {"status": "error", "message": "Job not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return None, error_response

        return job, None


class JobNumberLookupMixin(JobLookupMixin):
    """
    Specialized mixin for job_number-based lookups.
    Used for endpoints that receive job_number in request data.
    """

    def get_job_from_request_data(self, request, error_format="legacy"):
        """
        Extract job_number from request data and get job.

        Returns:
            tuple: (job_instance, error_response)
        """
        job_number = request.data.get("job_number")
        if not job_number:
            if error_format == "api":
                error_response = Response(
                    {"success": False, "error": "Job number is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                error_response = Response(
                    {"status": "error", "message": "Job number is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return None, error_response

        return self.get_job_or_404_response(
            job_number=job_number, error_format=error_format
        )
