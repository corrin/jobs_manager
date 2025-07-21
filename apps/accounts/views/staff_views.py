import logging

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.accounts.forms import StaffChangeForm, StaffCreationForm
from apps.accounts.models import Staff
from apps.accounts.serializers import KanbanStaffSerializer
from apps.accounts.utils import get_excluded_staff

logger = logging.getLogger(__name__)


class StaffListAPIView(generics.ListAPIView):
    """API endpoint for retrieving list of staff members for Kanban board.

    Supports filtering to return only actual users (excluding system/test accounts)
    based on the 'actual_users' query parameter.
    """

    queryset = Staff.objects.all()
    serializer_class = KanbanStaffSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="actual_users",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter to return only actual users (excluding system/test accounts). Pass "true" to filter.',
                required=False,
                enum=["true", "false"],
                default="false",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = KanbanStaffSerializer(queryset, many=True)
        return JsonResponse(serializer.data, safe=False)

    def get_queryset(self):
        actual_users_param = self.request.GET.get("actual_users", "false").lower()
        actual_users = actual_users_param == "true"

        if actual_users:
            excluded_ids_str = get_excluded_staff()
            # Convert string IDs to UUIDs for proper filtering
            from uuid import UUID

            excluded_ids = [UUID(id_str) for id_str in excluded_ids_str]
            queryset = Staff.objects.exclude(id__in=excluded_ids)
            return queryset
        else:
            return Staff.objects.all()

    def get_serializer_context(self):
        return {"request": self.request}


class StaffListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Display list of all staff members.

    Restricted to staff managers only.
    """

    model = Staff
    template_name = "accounts/staff/list_staff.html"
    context_object_name = "staff_list"

    def test_func(self):
        return self.request.user.is_staff_manager()


class StaffCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new staff member.

    Restricted to staff managers only. Uses StaffCreationForm for validation
    and redirects to staff list upon successful creation.
    """

    model = Staff
    form_class = StaffCreationForm
    template_name = "accounts/staff/create_staff.html"
    success_url = reverse_lazy("accounts:list_staff")

    def test_func(self):
        return self.request.user.is_staff_manager()


class StaffUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update existing staff member details.

    Accessible to staff managers or the staff member updating their own profile.
    Uses StaffChangeForm for validation and redirects to staff list upon success.
    """

    model = Staff
    form_class = StaffChangeForm
    template_name = "accounts/staff/update_staff.html"
    success_url = reverse_lazy("accounts:list_staff")

    def test_func(self):
        return (
            self.request.user.is_staff_manager()
            or self.request.user.pk == self.kwargs["pk"]
        )


def get_staff_rates(request, staff_id):
    """Retrieve wage rates for a specific staff member.

    Returns JSON response with staff member's wage rate information.
    Restricted to authenticated staff managers only.

    Args:
        request: HTTP request object
        staff_id: UUID of the staff member

    Returns:
        JsonResponse: Staff wage rate data or error message
    """
    if not request.user.is_authenticated or not request.user.is_staff_manager():
        return JsonResponse({"error": "Unauthorized"}, status=403)
    staff = get_object_or_404(Staff, id=staff_id)
    rates = {
        "wage_rate": float(staff.wage_rate),
        # "charge_out_rate": float(staff.charge_out_rate),
    }
    return JsonResponse(rates)
