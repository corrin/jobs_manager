"""
Job Quote Chat REST Views

REST API endpoints for managing chat conversations linked to jobs.
Follows the same pattern as other job REST views.
"""

import json
import logging
from typing import Any, Dict

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job, JobQuoteChat

logger = logging.getLogger(__name__)


class BaseJobQuoteChatView(APIView):
    """
    Base view for Job Quote Chat REST operations.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def parse_json_body(self, request) -> Dict[str, Any]:
        """Parse the JSON body of the request."""
        if not request.body:
            raise ValueError("Request body is empty")

        try:
            return json.loads(request.body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")

    def handle_error(self, error: Exception) -> Response:
        """Handle errors and return appropriate response."""
        error_message = str(error)

        if isinstance(error, ValueError):
            return Response(
                {"success": False, "error": error_message}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        elif "not found" in error_message.lower():
            return Response(
                {"success": False, "error": "Job not found", "code": "JOB_NOT_FOUND"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        else:
            logger.exception(f"Unhandled error in quote chat API: {error}")
            return Response(
                {"success": False, "error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@method_decorator(csrf_exempt, name="dispatch")
class JobQuoteChatHistoryView(BaseJobQuoteChatView):
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
            # Check if job exists
            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                return Response(
                    {"success": False, "error": "Job not found", "code": "JOB_NOT_FOUND"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get all chat messages for this job, ordered by timestamp
            messages = JobQuoteChat.objects.filter(job=job).order_by('timestamp')

            # Format messages according to the API spec
            formatted_messages = []
            for message in messages:
                formatted_messages.append({
                    "message_id": message.message_id,
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "metadata": message.metadata
                })

            return Response({
                "success": True,
                "data": {
                    "job_id": str(job.id),
                    "messages": formatted_messages
                }
            }, status=status.HTTP_200_OK)

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
            # Check if job exists
            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                return Response(
                    {"success": False, "error": "Job not found", "code": "JOB_NOT_FOUND"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Parse request body
            data = self.parse_json_body(request)

            # Validate required fields
            required_fields = ['message_id', 'role', 'content']
            for field in required_fields:
                if field not in data:
                    return Response(
                        {"success": False, "error": f"{field} is required"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Validate role
            if data['role'] not in ['user', 'assistant']:
                return Response(
                    {"success": False, "error": "role must be 'user' or 'assistant'"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if message_id already exists
            if JobQuoteChat.objects.filter(message_id=data['message_id']).exists():
                return Response(
                    {"success": False, "error": "message_id already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create the message
            message = JobQuoteChat.objects.create(
                job=job,
                message_id=data['message_id'],
                role=data['role'],
                content=data['content'],
                metadata=data.get('metadata', {})
            )

            return Response({
                "success": True,
                "data": {
                    "message_id": message.message_id,
                    "timestamp": message.timestamp.isoformat()
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return self.handle_error(e)

    def delete(self, request, job_id):
        """
        Delete all chat messages for a job (start fresh).
        """
        try:
            # Check if job exists
            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                return Response(
                    {"success": False, "error": "Job not found", "code": "JOB_NOT_FOUND"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Delete all messages for this job
            deleted_count, _ = JobQuoteChat.objects.filter(job=job).delete()

            return Response({
                "success": True,
                "data": {
                    "deleted_count": deleted_count
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_error(e)


@method_decorator(csrf_exempt, name="dispatch")
class JobQuoteChatMessageView(BaseJobQuoteChatView):
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
            # Check if job exists
            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                return Response(
                    {"success": False, "error": "Job not found", "code": "JOB_NOT_FOUND"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Find the message
            try:
                message = JobQuoteChat.objects.get(job=job, message_id=message_id)
            except JobQuoteChat.DoesNotExist:
                return Response(
                    {"success": False, "error": "Message not found", "code": "MESSAGE_NOT_FOUND"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Parse request body
            data = self.parse_json_body(request)

            # Update fields if provided
            if 'content' in data:
                message.content = data['content']
            
            if 'metadata' in data:
                # Merge metadata instead of replacing
                current_metadata = message.metadata or {}
                current_metadata.update(data['metadata'])
                message.metadata = current_metadata

            message.save()

            return Response({
                "success": True,
                "data": {
                    "message_id": message.message_id,
                    "content": message.content,
                    "metadata": message.metadata,
                    "timestamp": message.timestamp.isoformat()
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return self.handle_error(e)