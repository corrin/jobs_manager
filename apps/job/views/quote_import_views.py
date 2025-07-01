"""
Quote Import REST Views

REST endpoints for importing quotes from spreadsheets.
Follows clean code principles:
- Views as orchestrators only
- Delegation to service layer
- Proper error handling and response formatting
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job
from apps.job.serializers.costing_serializer import CostSetSerializer

logger = logging.getLogger(__name__)


class QuoteImportPreviewView(APIView):
    """
    DEPRECATED: Excel import functionality has been removed.
    Use Google Sheets integration instead via /quote/sync/ endpoints.

    POST /jobs/<job_id>/quote/import/preview/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        """Return deprecation notice"""
        return Response(
            {
                "error": "Excel import functionality has been removed. Please use Google Sheets integration instead.",
                "deprecated": True,
                "alternative": f"/jobs/{job_id}/quote/sync/preview/",
            },
            status=status.HTTP_410_GONE,
        )


class QuoteImportView(APIView):
    """
    DEPRECATED: Excel import functionality has been removed.
    Use Google Sheets integration instead via /quote/sync/ endpoints.

    POST /jobs/<job_id>/quote/import/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        """Return deprecation notice"""
        return Response(
            {
                "error": "Excel import functionality has been removed. Please use Google Sheets integration instead.",
                "deprecated": True,
                "alternative": f"/jobs/{job_id}/quote/sync/apply/",
            },
            status=status.HTTP_410_GONE,
        )


class QuoteImportStatusView(APIView):
    """
    Get current quote import status and latest quote information.

    GET /jobs/<job_id>/quote/status/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        """Get quote status for job"""
        # Early return: validate job exists
        job = get_object_or_404(Job, pk=job_id)

        try:
            # Get latest quote
            latest_quote = job.get_latest("quote")

            response_data = {
                "job_id": str(job.id),
                "job_name": job.name,
                "has_quote": latest_quote is not None,
            }

            if latest_quote:
                response_data.update(
                    {
                        "quote": CostSetSerializer(latest_quote).data,
                        "revision": latest_quote.rev,
                        "created": latest_quote.created,
                        "summary": latest_quote.summary,
                    }
                )

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting quote status for job {job_id}: {str(e)}")
            return Response(
                {"error": f"Failed to get quote status: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
