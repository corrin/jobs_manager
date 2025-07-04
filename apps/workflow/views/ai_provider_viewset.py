from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.workflow.models import AIProvider
from apps.workflow.serializers import (
    AIProviderCreateUpdateSerializer,
    AIProviderSerializer,
)


class AIProviderViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows AI Providers to be viewed or edited.

    Provides standard CRUD operations and a custom action to set a
    provider as the default for the company.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the AI providers
        for the currently authenticated user's company.
        """
        user = self.request.user
        # Ensure user is a staff member and associated with a company
        if hasattr(user, "staff") and user.staff.company:
            return AIProvider.objects.filter(company=user.staff.company).order_by(
                "name"
            )
        return AIProvider.objects.none()

    def get_serializer_class(self):
        """
        Return different serializers for read and write operations.
        - `AIProviderSerializer` for read operations (doesn't expose API key).
        - `AIProviderCreateUpdateSerializer` for write operations (handles API key).
        """
        if self.action in ["create", "update", "partial_update"]:
            return AIProviderCreateUpdateSerializer
        return AIProviderSerializer

    def perform_create(self, serializer):
        """
        Associate the new AI Provider with the user's company automatically.
        """
        user = self.request.user
        if hasattr(user, "staff") and user.staff.company:
            serializer.save(company=user.staff.company)
        else:
            # This case should ideally not be reached due to permissions/queryset logic
            # but serves as a safeguard.
            raise permissions.PermissionDenied("User is not associated with a company.")

    @action(detail=True, methods=["post"], url_path="set-default")
    @transaction.atomic
    def set_default(self, request, pk=None):
        """
        Set this provider as the default for the company.
        This will atomically unset any other provider that is currently the default
        for the same company.
        """
        provider = self.get_object()
        company = provider.company

        # Ensure the user has permission for the company of the object
        if not (
            hasattr(request.user, "staff") and request.user.staff.company == company
        ):
            raise permissions.PermissionDenied()

        # Unset other defaults for the same company and provider type
        company.ai_providers.filter(provider_type=provider.provider_type).exclude(
            pk=provider.pk
        ).update(default=False)

        # Set the new default
        provider.default = True
        provider.save(update_fields=["default"])

        serializer = self.get_serializer(provider)
        return Response(serializer.data, status=status.HTTP_200_OK)
