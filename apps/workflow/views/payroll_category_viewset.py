from rest_framework import permissions, viewsets

from apps.workflow.models import PayrollCategory
from apps.workflow.serializers import (
    PayrollCategoryCreateUpdateSerializer,
    PayrollCategorySerializer,
)


class PayrollCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for PayrollCategory CRUD operations.

    Provides standard CRUD for managing payroll category mappings
    that link job types and work rates to Xero payroll posting behavior.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PayrollCategory.objects.all().order_by("name")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PayrollCategoryCreateUpdateSerializer
        return PayrollCategorySerializer
