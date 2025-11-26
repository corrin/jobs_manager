import logging

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job
from apps.job.serializers.job_serializer import WorkshopPDFResponseSerializer
from apps.job.services.workshop_pdf_service import create_workshop_pdf

logger = logging.getLogger(__name__)


class WorkshopPDFView(APIView):
    """
    API view for generating and serving workshop PDF documents for jobs.

    This view creates printable workshop PDFs that contain job details,
    specifications, and any relevant files marked for workshop printing.
    The generated PDF is returned inline for direct printing or viewing
    in the browser.

    GET: Generates a workshop PDF for the specified job ID and returns
         it as a file response with appropriate headers for printing.
    """

    serializer_class = WorkshopPDFResponseSerializer

    def get(self, request, job_id):
        """Generate and return a workshop PDF for printing."""
        try:
            job = get_object_or_404(Job, pk=job_id)

            # Generate the workshop PDF
            pdf_buffer = create_workshop_pdf(job)

            # Return the PDF for printing
            response = FileResponse(
                pdf_buffer,
                as_attachment=False,
                filename=f"workshop_{job.job_number}.pdf",
                content_type="application/pdf",
            )

            # Add header to trigger print dialog
            response["Content-Disposition"] = (
                f'inline; filename="workshop_{job.job_number}.pdf"'
            )

            return response

        except Exception as e:
            logger.exception(f"Error generating workshop PDF for job {job_id}")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
