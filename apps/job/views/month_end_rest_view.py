import json
import logging
from typing import Any, Dict

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.services.month_end_service import MonthEndService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class MonthEndRestView(APIView):
    def get(self, request):
        jobs = MonthEndService.get_special_jobs_data()
        stock = MonthEndService.get_stock_job_data()
        serialized_jobs = [
            {
                "job_id": str(item["job"].id),
                "job_number": item["job"].job_number,
                "job_name": item["job"].name,
                "client_name": item["job"].client.name if item["job"].client else "",
                "history": [
                    {
                        "date": h["date"],
                        "total_hours": float(h["total_hours"]),
                        "total_dollars": float(h["total_dollars"]),
                    }
                    for h in item["history"]
                ],
                "total_hours": float(item["total_hours"]),
                "total_dollars": float(item["total_dollars"]),
            }
            for item in jobs
        ]
        stock_serialized = {
            "job_id": str(stock["job"].id),
            "job_number": stock["job"].job_number,
            "job_name": stock["job"].name,
            "history": [
                {
                    "date": h["date"],
                    "material_line_count": h["material_line_count"],
                    "material_cost": float(h["material_cost"]),
                }
                for h in stock["history"]
            ],
        }
        return Response(
            {"jobs": serialized_jobs, "stock_job": stock_serialized},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        try:
            payload: Dict[str, Any] = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return Response(
                {"error": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST
            )
        job_ids = payload.get("job_ids", [])
        if not isinstance(job_ids, list):
            return Response(
                {"error": "job_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST
            )
        processed, errors = MonthEndService.process_jobs(job_ids)
        return Response(
            {
                "processed": [str(job.id) for job in processed],
                "errors": errors,
            },
            status=status.HTTP_200_OK,
        )
