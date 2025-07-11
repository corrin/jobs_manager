"""
Quote Sync Views

REST endpoints for managing quote spreadsheets integrated with Google Sheets.
Provides functionality to:
- Link jobs to Google Sheets quote templates
- Preview quote changes from linked sheets
- Apply quote changes from linked sheets
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.job.models import Job
from apps.job.serializers.costing_serializer import CostSetSerializer
from apps.job.serializers.quote_sync_serializer import (
    ApplyQuoteErrorResponseSerializer,
    ApplyQuoteResponseSerializer,
    LinkQuoteSheetRequestSerializer,
    LinkQuoteSheetResponseSerializer,
    PreviewQuoteResponseSerializer,
    QuoteSyncErrorResponseSerializer,
)
from apps.job.services import quote_sync_service

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def link_quote_sheet(request: Request, pk: str) -> Response:
    """
    Link a job to a Google Sheets quote template.

    POST /job/rest/jobs/<uuid:pk>/quote/link/

    Request body (optional):
    {
        "template_url": "https://docs.google.com/spreadsheets/d/..."
    }

    Returns:
    {
        "sheet_url": "https://docs.google.com/spreadsheets/d/.../edit",
        "sheet_id": "spreadsheet_id",
        "job_id": "job_uuid"
    }
    """
    try:
        # Get job
        try:
            job = Job.objects.get(pk=pk)
        except Job.DoesNotExist:
            error_response = {"error": "Job not found"}
            error_serializer = QuoteSyncErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

        # Validate input data
        input_serializer = LinkQuoteSheetRequestSerializer(data=request.data)
        if not input_serializer.is_valid():
            error_response = {"error": f"Invalid input: {input_serializer.errors}"}
            error_serializer = QuoteSyncErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        # Extract template URL from request if provided
        template_url = input_serializer.validated_data.get("template_url")

        # Link quote sheet
        quote_sheet = quote_sync_service.link_quote_sheet(job, template_url)

        response_data = {
            "sheet_url": quote_sheet.sheet_url,
            "sheet_id": quote_sheet.sheet_id,
            "job_id": str(job.id),
        }

        response_serializer = LinkQuoteSheetResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except RuntimeError as e:
        logger.error(f"Error linking quote sheet for job {pk}: {str(e)}")
        error_response = {"error": str(e)}
        error_serializer = QuoteSyncErrorResponseSerializer(error_response)
        return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error linking quote sheet for job {pk}: {str(e)}")
        error_response = {"error": "An unexpected error occurred"}
        error_serializer = QuoteSyncErrorResponseSerializer(error_response)
        return Response(
            error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def preview_quote(request: Request, pk: str) -> Response:
    """
    Preview quote import from linked Google Sheet.

    POST /job/rest/jobs/<uuid:pk>/quote/preview/

    Returns:
    The preview dictionary from quote_sync_service.preview_quote()
    """
    try:
        # Get job
        try:
            job = Job.objects.get(pk=pk)
        except Job.DoesNotExist:
            error_response = {"error": "Job not found"}
            error_serializer = QuoteSyncErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

        # Preview quote
        preview_data = quote_sync_service.preview_quote(job)

        # Serialize the preview data
        response_serializer = PreviewQuoteResponseSerializer(preview_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except RuntimeError as e:
        logger.error(f"Error previewing quote for job {pk}: {str(e)}")
        error_response = {"error": str(e)}
        error_serializer = QuoteSyncErrorResponseSerializer(error_response)
        return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error previewing quote for job {pk}: {str(e)}")
        error_response = {"error": "An unexpected error occurred"}
        error_serializer = QuoteSyncErrorResponseSerializer(error_response)
        return Response(
            error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def apply_quote(request: Request, pk: str) -> Response:
    """
    Apply quote import from linked Google Sheet.

    POST /job/rest/jobs/<uuid:pk>/quote/apply/

    Returns:
    {
        "success": true,
        "cost_set": CostSetSerializer(...),
        "changes": {
            "additions": [...],
            "updates": [...],
            "deletions": [...]
        }
    }
    """
    try:
        # Get job
        try:
            job = Job.objects.get(pk=pk)
        except Job.DoesNotExist:
            error_response = {"error": "Job not found"}
            error_serializer = QuoteSyncErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

        # Apply quote
        result = quote_sync_service.apply_quote(job)

        if result.success:
            # Serialize the cost set if available
            cost_set_data = None
            if result.cost_set:
                cost_set_data = CostSetSerializer(result.cost_set).data

            # Convert DraftLine objects to dictionaries for JSON serialization
            def draft_line_to_dict(draft_line):
                return {
                    "kind": draft_line.kind,
                    "desc": draft_line.desc,
                    "quantity": float(draft_line.quantity),
                    "unit_cost": float(draft_line.unit_cost),
                    "unit_rev": float(draft_line.unit_rev),
                    "total_cost": float(draft_line.quantity * draft_line.unit_cost),
                    "total_rev": float(draft_line.quantity * draft_line.unit_rev),
                }

            response_data = {
                "success": True,
                "cost_set": cost_set_data,
                "draft_lines": (
                    [draft_line_to_dict(line) for line in result.diff_result.to_add]
                    if result.diff_result
                    else []
                ),
                "changes": {
                    "additions": (
                        [draft_line_to_dict(line) for line in result.diff_result.to_add]
                        if result.diff_result
                        else []
                    ),
                    "updates": (
                        [
                            draft_line_to_dict(draft_line)
                            for _, draft_line in result.diff_result.to_update
                        ]
                        if result.diff_result
                        else []
                    ),
                    "deletions": (
                        [
                            {
                                "kind": line.kind,
                                "desc": line.desc,
                                "quantity": float(line.quantity),
                                "unit_cost": float(line.unit_cost),
                                "unit_rev": float(line.unit_rev),
                            }
                            for line in result.diff_result.to_delete
                        ]
                        if result.diff_result
                        else []
                    ),
                },
            }

            response_serializer = ApplyQuoteResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            error_response = {"success": False, "error": result.error_message}
            error_serializer = ApplyQuoteErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

    except RuntimeError as e:
        logger.error(f"Error applying quote for job {pk}: {str(e)}")
        error_response = {"error": str(e)}
        error_serializer = QuoteSyncErrorResponseSerializer(error_response)
        return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error applying quote for job {pk}: {str(e)}")
        error_response = {"error": "An unexpected error occurred"}
        error_serializer = QuoteSyncErrorResponseSerializer(error_response)
        return Response(
            error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
