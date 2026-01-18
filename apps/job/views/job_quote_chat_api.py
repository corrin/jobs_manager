"""
Job Quote Chat Interaction API Views

This file contains the API view that handles the real-time interaction
between the user and the AI chat assistant.
"""

import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job
from apps.job.serializers import (
    JobQuoteChatInteractionErrorResponseSerializer,
    JobQuoteChatInteractionSerializer,
    JobQuoteChatInteractionSuccessResponseSerializer,
)
from apps.job.services.chat_service import ChatService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class JobQuoteChatInteractionView(APIView):
    """
    API view to handle real-time interaction with the AI chat assistant.

    This view connects the frontend chat interface to the MCPChatService,
    which orchestrates the call to the LLM, handles tool use, and returns
    the final generated response.
    """

    # ---------------------------------------------------------------------
    # DRF configuration
    # ---------------------------------------------------------------------

    # Only allow POST (and implicit OPTIONS for CORS pre-flight)
    permission_classes = [IsAuthenticated]
    http_method_names = ["post", "options"]
    serializer_class = JobQuoteChatInteractionSerializer

    @extend_schema(
        request=JobQuoteChatInteractionSerializer,
        responses={
            201: OpenApiResponse(
                response=JobQuoteChatInteractionSuccessResponseSerializer,
                description="AI response generated successfully",
            ),
            400: OpenApiResponse(
                response=JobQuoteChatInteractionErrorResponseSerializer,
                description="Invalid input data or configuration error",
            ),
            404: OpenApiResponse(
                response=JobQuoteChatInteractionErrorResponseSerializer,
                description="Job not found",
            ),
            500: OpenApiResponse(
                response=JobQuoteChatInteractionErrorResponseSerializer,
                description="Internal server error",
            ),
        },
        summary="Get AI assistant response",
        description="Sends user message to AI assistant and returns the generated response",
    )
    def post(self, request, job_id):
        """
        Receives a user message, sends it to the MCPChatService for processing,
        and returns the AI's final response.

        The frontend is expected to first save the user's message via the
        JobQuoteChatHistoryView, and then call this endpoint to get the
        assistant's reply.
        """
        # Validate input data
        serializer = JobQuoteChatInteractionSerializer(data=request.data)
        if not serializer.is_valid():
            error_response = {
                "success": False,
                "error": "Invalid input data",
                "details": serializer.errors,
            }
            error_serializer = JobQuoteChatInteractionErrorResponseSerializer(
                error_response
            )
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        user_message = serializer.validated_data["message"]
        mode = serializer.validated_data.get("mode", "AUTO")

        try:
            # Instantiate the chat service
            chat_service = ChatService()

            # Use mode-based system as the primary implementation
            # AUTO mode means the system will infer the appropriate mode
            if mode == "AUTO":
                mode = None  # Let the system infer

            logger.info(
                f"Processing request for job {job_id} with mode: {mode or 'AUTO (will infer)'}"
            )
            assistant_message_obj = chat_service.generate_mode_response(
                job_id=job_id, user_message=user_message, mode=mode
            )

            # Serialize the final assistant message to return to the client
            response_data = {"success": True, "data": assistant_message_obj}
            response_serializer = JobQuoteChatInteractionSuccessResponseSerializer(
                response_data
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Job.DoesNotExist:
            error_data = {
                "success": False,
                "error": "Job not found",
                "code": "JOB_NOT_FOUND",
            }
            error_serializer = JobQuoteChatInteractionErrorResponseSerializer(
                error_data
            )
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

        except ValueError as e:
            # This can catch configuration errors from the service,
            # e.g., "No default Gemini AI provider configured"
            logger.error(
                f"Configuration error in chat interaction for job {job_id}: {e}"
            )
            error_data = {"success": False, "error": str(e)}
            error_serializer = JobQuoteChatInteractionErrorResponseSerializer(
                error_data
            )
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(
                f"Unhandled error in chat interaction for job {job_id}: {e}"
            )
            error_data = {
                "success": False,
                "error": "An internal error occurred while processing your request.",
            }
            error_serializer = JobQuoteChatInteractionErrorResponseSerializer(
                error_data
            )
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
