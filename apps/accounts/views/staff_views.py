from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.accounts.forms import StaffChangeForm, StaffCreationForm
from apps.accounts.models import Staff
from apps.accounts.serializers import KanbanStaffSerializer
from apps.accounts.utils import get_excluded_staff


class StaffListAPIView(generics.ListAPIView):
    queryset = Staff.objects.all()
    serializer_class = KanbanStaffSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = KanbanStaffSerializer(queryset, many=True)
        return JsonResponse(serializer.data, safe=False)

    def get_queryset(self):
        actual_users_param = self.request.GET.get("actual_users", "false").lower()
        actual_users = actual_users_param == "true"
        if actual_users:
            excluded_ids = get_excluded_staff()
            return Staff.objects.exclude(id__in=excluded_ids)
        return Staff.objects.all()

    def get_serializer_context(self):
        return {"request": self.request}


class StaffListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Staff
    template_name = "accounts/staff/list_staff.html"
    context_object_name = "staff_list"

    def test_func(self):
        return self.request.user.is_staff_manager()


class StaffCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Staff
    form_class = StaffCreationForm
    template_name = "accounts/staff/create_staff.html"
    success_url = reverse_lazy("accounts:list_staff")

    def test_func(self):
        return self.request.user.is_staff_manager()


class StaffUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
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
    if not request.user.is_authenticated or not request.user.is_staff_manager():
        return JsonResponse({"error": "Unauthorized"}, status=403)
    staff = get_object_or_404(Staff, id=staff_id)
    rates = {
        "wage_rate": float(staff.wage_rate),
        # "charge_out_rate": float(staff.charge_out_rate),
    }
    return JsonResponse(rates)
