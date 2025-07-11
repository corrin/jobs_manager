from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.workflow.api.pagination import FiftyPerPagePagination
from apps.workflow.models import AppError
from apps.workflow.serializers import AppErrorSerializer


class AppErrorListAPIView(ListAPIView):
    """
    API view for listing application errors.

    Returns a paginated list of all AppError records ordered by timestamp
    (most recent first). Includes filtering capabilities for debugging and
    monitoring application issues.

    Endpoint: /api/app-errors/
    """

    queryset = AppError.objects.all().order_by("-timestamp")
    serializer_class = AppErrorSerializer
    pagination_class = FiftyPerPagePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["app", "severity", "resolved", "job_id", "user_id"]
    search_fields = ["message", "function", "file"]


class AppErrorDetailAPIView(RetrieveAPIView):
    """
    API view for retrieving a single application error.

    Returns detailed information about a specific AppError record
    including error message, context, location, and resolution status.
    Used for investigating specific application failures.

    Endpoint: /api/app-errors/<id>/
    """

    queryset = AppError.objects.all()
    serializer_class = AppErrorSerializer


class AppErrorViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for AppError with filtering capabilities and resolution actions.

    Provides list, retrieve, and resolution management for application errors.
    Includes comprehensive filtering and search capabilities for error analysis.

    Endpoints:
    - GET /api/app-errors/
    - GET /api/app-errors/<id>/
    - POST /api/app-errors/<id>/mark_resolved/
    - POST /api/app-errors/<id>/mark_unresolved/
    """

    queryset = AppError.objects.all().order_by("-timestamp")
    serializer_class = AppErrorSerializer
    pagination_class = FiftyPerPagePagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = {
        "app": ["exact", "icontains"],
        "file": ["exact", "icontains"],
        "function": ["exact", "icontains"],
        "severity": ["exact", "gte", "lte"],
        "job_id": ["exact"],
        "user_id": ["exact"],
        "resolved": ["exact"],
        "timestamp": ["gte", "lte"],
    }
    search_fields = ["message", "function", "file", "app"]
    ordering_fields = ["timestamp", "severity", "app", "resolved"]
    ordering = ["-timestamp"]

    @action(detail=True, methods=["post"])
    def mark_resolved(self, request, pk=None):
        """Mark an error as resolved."""
        error = self.get_object()

        # Get the current user (staff member)
        if hasattr(request.user, "staff_profile"):
            staff_member = request.user.staff_profile
        else:
            staff_member = None

        error.mark_resolved(staff_member)

        return Response(
            {
                "status": "resolved",
                "resolved_by": staff_member.id if staff_member else None,
                "resolved_timestamp": error.resolved_timestamp,
            }
        )

    @action(detail=True, methods=["post"])
    def mark_unresolved(self, request, pk=None):
        """Mark an error as unresolved."""
        error = self.get_object()

        # Get the current user (staff member)
        if hasattr(request.user, "staff_profile"):
            staff_member = request.user.staff_profile
        else:
            staff_member = None

        error.mark_unresolved(staff_member)

        return Response(
            {
                "status": "unresolved",
                "resolved": False,
                "resolved_by": None,
                "resolved_timestamp": None,
            }
        )
