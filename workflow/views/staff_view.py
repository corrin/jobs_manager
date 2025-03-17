from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from workflow.forms import StaffChangeForm, StaffCreationForm
from workflow.serializers.staff_serializer import StaffNameSerializer
from workflow.utils import get_excluded_staff


Staff = get_user_model()


class StaffListAPIView(generics.ListAPIView):
    queryset = Staff.objects.all()
    serializer_class = StaffNameSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset(request)
        serializer = StaffNameSerializer(queryset, many=True)
        return JsonResponse(serializer.data, safe=False)
    
    def get_queryset(self, request):
        actual_users = eval(request.headers.get("X-Actual-Users", "False"))
        match actual_users:
            case True:
                excluded_ids = get_excluded_staff()
                return Staff.objects.exclude(id__in=excluded_ids)
            case False:
                return Staff.objects.all()


class StaffListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Staff
    template_name = "list_staff.html"
    context_object_name = "staff_list"

    def test_func(self):
        return self.request.user.is_staff_manager()


class StaffCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Staff
    form_class = StaffCreationForm
    template_name = "create_staff.html"
    success_url = reverse_lazy("list_staff")

    def test_func(self):
        return self.request.user.is_staff_manager()


class StaffUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Staff
    form_class = StaffChangeForm
    template_name = "update_staff.html"
    success_url = reverse_lazy("list_staff")

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
