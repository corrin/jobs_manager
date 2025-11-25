"""
AWS Instance Management API Views
"""

import json
import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.workflow.exceptions import AlreadyLoggedException
from apps.workflow.serializers import AWSInstanceStatusResponseSerializer
from apps.workflow.services.aws_service import AWSService
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


def _build_error_payload(message: str, exc: Exception) -> dict[str, object]:
    if isinstance(exc, AlreadyLoggedException):
        root_exc = exc.original
        error_id = exc.app_error_id
    else:
        app_error = persist_app_error(exc)
        root_exc = exc
        error_id = getattr(app_error, "id", None)

    payload: dict[str, object] = {
        "success": False,
        "error": message,
        "details": str(root_exc),
    }
    if error_id:
        payload["error_id"] = str(error_id)
    return payload


def _drf_error_response(message: str, exc: Exception) -> Response:
    payload = _build_error_payload(message, exc)
    return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _json_error_response(message: str, exc: Exception) -> JsonResponse:
    payload = _build_error_payload(message, exc)
    return JsonResponse(payload, status=500)


@extend_schema(responses=AWSInstanceStatusResponseSerializer)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_instance_status(request):
    """Get current status of the UAT instance"""
    try:
        aws_service = AWSService()
        result = aws_service.get_instance_status()

        if result["success"]:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return Response(
            {"success": False, "error": "AWS configuration error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:
        logger.error(f"Unexpected error getting instance status: {str(exc)}")
        return _drf_error_response("Internal server error", exc)


@extend_schema(request=None, responses=AWSInstanceStatusResponseSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_instance(request):
    """Start the UAT instance"""
    try:
        aws_service = AWSService()
        result = aws_service.start_instance()

        if result["success"]:
            logger.info(f"Instance start initiated by user {request.user.email}")
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return Response(
            {"success": False, "error": "AWS configuration error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:
        logger.error(f"Unexpected error starting instance: {str(exc)}")
        return _drf_error_response("Internal server error", exc)


@extend_schema(request=None, responses=AWSInstanceStatusResponseSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def stop_instance(request):
    """Stop the UAT instance"""
    try:
        aws_service = AWSService()
        result = aws_service.stop_instance()

        if result["success"]:
            logger.info(f"Instance stop initiated by user {request.user.email}")
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return Response(
            {"success": False, "error": "AWS configuration error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:
        logger.error(f"Unexpected error stopping instance: {str(exc)}")
        return _drf_error_response("Internal server error", exc)


@extend_schema(request=None, responses=AWSInstanceStatusResponseSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reboot_instance(request):
    """Reboot the UAT instance"""
    try:
        aws_service = AWSService()
        result = aws_service.reboot_instance()

        if result["success"]:
            logger.info(f"Instance reboot initiated by user {request.user.email}")
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return Response(
            {"success": False, "error": "AWS configuration error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    except Exception as exc:
        logger.error(f"Unexpected error rebooting instance: {str(exc)}")
        return _drf_error_response("Internal server error", exc)


@method_decorator(csrf_exempt, name="dispatch")
class AWSInstanceManagementView(View):
    """
    Combined view for AWS instance management operations
    Handles all instance operations through a single endpoint with action parameter
    """

    def dispatch(self, request, *args, **kwargs):
        """Ensure user is authenticated before processing any requests"""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "Authentication required"}, status=401
            )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """Get instance status"""
        return self._handle_request(request, "status")

    def post(self, request):
        """Handle POST requests for instance operations"""
        try:
            data = json.loads(request.body) if request.body else {}
            action = data.get("action", request.GET.get("action"))

            if not action:
                return JsonResponse(
                    {"success": False, "error": "Action parameter is required"},
                    status=400,
                )

            return self._handle_request(request, action)

        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON in request body"}, status=400
            )

    def _handle_request(self, request, action):
        """Handle the actual AWS operation based on action"""
        try:
            aws_service = AWSService()

            if action == "status":
                result = aws_service.get_instance_status()
            elif action == "start":
                result = aws_service.start_instance()
                if result["success"]:
                    logger.info(
                        f"Instance start initiated by user {request.user.email}"
                    )
            elif action == "stop":
                result = aws_service.stop_instance()
                if result["success"]:
                    logger.info(f"Instance stop initiated by user {request.user.email}")
            elif action == "reboot":
                result = aws_service.reboot_instance()
                if result["success"]:
                    logger.info(
                        f"Instance reboot initiated by user {request.user.email}"
                    )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            f"Unknown action: {action}. Valid actions are: "
                            "status, start, stop, reboot"
                        ),
                    },
                    status=400,
                )

            status_code = 200 if result["success"] else 400
            return JsonResponse(result, status=status_code)

        except ValueError as e:
            logger.error(f"Configuration error: {str(e)}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "AWS configuration error",
                    "details": str(e),
                },
                status=500,
            )
        except Exception as exc:
            logger.error(f"Unexpected error in AWS operation '{action}': {str(exc)}")
            return _json_error_response("Internal server error", exc)
