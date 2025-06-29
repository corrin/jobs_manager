from django_apscheduler.models import DjangoJob, DjangoJobExecution
from rest_framework import filters, status, viewsets
from rest_framework.response import Response

from .serializers_django_jobs import DjangoJobExecutionSerializer, DjangoJobSerializer


class DjangoJobViewSet(viewsets.ModelViewSet):
    queryset = DjangoJob.objects.all().order_by("next_run_time")
    serializer_class = DjangoJobSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["id", "name"]


class DjangoJobExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DjangoJobExecution.objects.all().order_by("-run_time")
    serializer_class = DjangoJobExecutionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["job_id", "status", "exception"]
