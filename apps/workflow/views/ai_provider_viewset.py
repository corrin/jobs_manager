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
        Return all AI providers since company is a singleton.
        """
        return AIProvider.objects.all().order_by("name")

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
        Save the new AI Provider.
        """
        serializer.save()

    @action(detail=True, methods=["post"], url_path="set-default")
    @transaction.atomic
    def set_default(self, request, pk=None):
        """
        Set this provider as the default.
        This will atomically unset any other provider that is currently the default.
        """
        provider = self.get_object()

        # Unset other defaults for the same provider type
        AIProvider.objects.filter(provider_type=provider.provider_type).exclude(
            pk=provider.pk
        ).update(default=False)

        # Set the new default
        provider.default = True
        provider.save(update_fields=["default"])

        serializer = self.get_serializer(provider)
        return Response(serializer.data, status=status.HTTP_200_OK)
