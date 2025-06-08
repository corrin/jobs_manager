import logging

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.job.models import Job
from apps.job.services.import_quote_service import import_quote_from_excel

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@transaction.atomic
def import_quote(request, job_id):
    job = get_object_or_404(Job, id=job_id)

    file = request.FILES.get("file")
    if not file:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    job_pricing_id = request.POST.get("job_pricing_id")

    try:
        result = import_quote_from_excel(
            job=job, file=file, job_pricing_id=job_pricing_id
        )
        return JsonResponse(result)
    except Exception as exc:
        logger.exception("Error importing quote")
        return JsonResponse({"error": str(exc)}, status=400)
