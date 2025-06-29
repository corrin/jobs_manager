"""
Job Quote Chat REST Views

REST API endpoints for managing chat conversations linked to jobs.
Follows the same pattern as other job REST views.
"""

import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.mixins import JobLookupMixin
from apps.job.models import Job, JobQuoteChat
from apps.job.serializers import JobQuoteChatSerializer, JobQuoteChatUpdateSerializer

logger = logging.getLogger(__name__)


class BaseJobQuoteChatView(APIView):
    """
    Base view for Job Quote Chat REST operations.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_job_or_404(self, job_id):
        """Get job by ID or raise Job.DoesNotExist."""
        return Job.objects.get(id=job_id)

    def get_message_or_404(self, job, message_id):
        """Get message by job and message_id or raise JobQuoteChat.DoesNotExist."""
        return JobQuoteChat.objects.get(job=job, message_id=message_id)

    def handle_error(self, error: Exception) -> Response:
        """Handle errors and return appropriate response using match-case."""
        match error:
            case ValueError():
                return Response(
                    {"success": False, "error": str(error)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            case Job.DoesNotExist():
                return Response(
                    {
                        "success": False,
                        "error": "Job not found",
                        "code": "JOB_NOT_FOUND",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            case JobQuoteChat.DoesNotExist():
                return Response(
                    {
                        "success": False,
                        "error": "Message not found",
                        "code": "MESSAGE_NOT_FOUND",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            case _:
                logger.exception(f"Unhandled error in quote chat API: {error}")
                return Response(
                    {"success": False, "error": "Internal server error"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


@method_decorator(csrf_exempt, name="dispatch")
class JobQuoteChatHistoryView(JobLookupMixin, BaseJobQuoteChatView):
    """
    REST view for getting and managing chat history for a job.

    GET: Load all chat messages for a specific job
    POST: Save a new chat message (user or assistant)
    DELETE: Clear all chat history for a job
    """

    def get(self, request, job_id):
        """
        Load all chat messages for a specific job.

        Response format matches job_quote_chat_plan.md specification.
        """
        try:
            # Get job using utility method
            job = self.get_job_or_404(job_id)

            # Check if job exists
            job, error_response = self.get_job_or_404_response(error_format="api")
            if error_response:
                return error_response

            # Get all chat messages for this job, ordered by timestamp
            messages = JobQuoteChat.objects.filter(job=job).order_by("timestamp")

            # Format messages according to the API spec
            formatted_messages = []
            for message in messages:
                formatted_messages.append(
                    {
                        "message_id": message.message_id,
                        "role": message.role,
                        "content": message.content,
                        "timestamp": message.timestamp.isoformat(),
                        "metadata": message.metadata,
                    }
                )

            return Response(
                {
                    "success": True,
                    "data": {"job_id": str(job.id), "messages": formatted_messages},
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return self.handle_error(e)

    def post(self, request, job_id):
        """
        Save a new chat message (user or assistant).

        Expected JSON:
        {
            "message_id": "user-1234567892",
            "role": "user",
            "content": "Actually, make that 5 boxes instead",
            "metadata": {}
        }
        """
        try:
            # Get job using utility method
            job = self.get_job_or_404(job_id)

            # Check if job exists
            job, error_response = self.get_job_or_404_response(error_format="api")
            if error_response:
                return error_response

            # Validate data using serializer
            serializer = JobQuoteChatSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Create the message with job relationship
            message = serializer.save(job=job)

            return Response(
                {
                    "success": True,
                    "data": {
                        "message_id": message.message_id,
                        "timestamp": message.timestamp.isoformat(),
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return self.handle_error(e)

    def delete(self, request, job_id):
        """
        Delete all chat messages for a job (start fresh).
        """
        try:
            # Get job using utility method
            job = self.get_job_or_404(job_id)

            # Check if job exists
            job, error_response = self.get_job_or_404_response(error_format="api")
            if error_response:
                return error_response

            # Delete all messages for this job
            deleted_count, _ = JobQuoteChat.objects.filter(job=job).delete()

            return Response(
                {"success": True, "data": {"deleted_count": deleted_count}},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return self.handle_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobQuoteChatMessageView(JobLookupMixin, BaseJobQuoteChatView):
    """
    REST view for updating individual chat messages.

    PATCH: Update an existing message (useful for streaming responses)
    """

    def patch(self, request, job_id, message_id):
        """
        Update an existing message (useful for streaming responses).

        Expected JSON:
        {
            "content": "Updated message content",
            "metadata": {"final": true}
        }
        """
        try:
            # Get job and message using utility methods
            job = self.get_job_or_404(job_id)
            message = self.get_message_or_404(job, message_id)

            # Check if job exists
            job, error_response = self.get_job_or_404_response(error_format="api")
            if error_response:
                return error_response

            # Validate and update using serializer
            serializer = JobQuoteChatUpdateSerializer(
                message, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            updated_message = serializer.save()

            return Response(
                {
                    "success": True,
                    "data": {
                        "message_id": updated_message.message_id,
                        "content": updated_message.content,
                        "metadata": updated_message.metadata,
                        "timestamp": updated_message.timestamp.isoformat(),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return self.handle_error(e)
