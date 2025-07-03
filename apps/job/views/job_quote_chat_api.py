"""
Job Quote Chat Interaction API Views

This file contains the API view that handles the real-time interaction
between the user and the AI chat assistant.
"""

import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job
from apps.job.serializers import JobQuoteChatSerializer
from apps.job.services.gemini_chat_service import GeminiChatService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class JobQuoteChatInteractionView(APIView):
    """
    API view to handle real-time interaction with the AI chat assistant.

    This view connects the frontend chat interface to the MCPChatService,
    which orchestrates the call to the LLM, handles tool use, and returns
    the final generated response.
    """

    def post(self, request, job_id):
        """
        Receives a user message, sends it to the MCPChatService for processing,
        and returns the AI's final response.

        The frontend is expected to first save the user's message via the
        JobQuoteChatHistoryView, and then call this endpoint to get the
        assistant's reply.
        """
        user_message = request.data.get("message")

        if not user_message:
            return Response(
                {"success": False, "error": "Message content is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Instantiate the chat service
            chat_service = GeminiChatService()

            # The service handles the entire LLM interaction, including tool use
            # and saving the final assistant message to the database.
            # It returns the persisted assistant message object.
            assistant_message_obj = chat_service.generate_ai_response(
                job_id=job_id, user_message=user_message
            )

            # Serialize the final assistant message to return to the client
            serializer = JobQuoteChatSerializer(assistant_message_obj)

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        except Job.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "Job not found",
                    "code": "JOB_NOT_FOUND",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as e:
            # This can catch configuration errors from the service,
            # e.g., "No default Gemini AI provider configured"
            logger.error(f"Configuration error in chat interaction for job {job_id}: {e}")
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception(
                f"Unhandled error in chat interaction for job {job_id}: {e}"
            )
            return Response(
                {
                    "success": False,
                    "error": "An internal error occurred while processing your request.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
