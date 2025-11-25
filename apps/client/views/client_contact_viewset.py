"""
ClientContact ViewSet

ViewSet for ClientContact CRUD operations using DRF's ModelViewSet.
Provides list, create, retrieve, update, partial_update, and destroy actions.
"""

from rest_framework import permissions, viewsets

from apps.client.models import ClientContact
from apps.client.serializers import ClientContactSerializer


class ClientContactViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ClientContact CRUD operations.

    Endpoints:
    - GET    /api/clients/contacts/           - list all contacts
    - POST   /api/clients/contacts/           - create contact
    - GET    /api/clients/contacts/<id>/      - retrieve contact
    - PUT    /api/clients/contacts/<id>/      - full update
    - PATCH  /api/clients/contacts/<id>/      - partial update
    - DELETE /api/clients/contacts/<id>/      - soft delete (sets is_active=False)

    Query Parameters:
    - client_id: Filter contacts by client UUID
    """

    queryset = ClientContact.objects.all()
    serializer_class = ClientContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter to only active contacts, optionally filtered by client_id.
        """
        queryset = ClientContact.objects.filter(is_active=True)
        client_id = self.request.query_params.get("client_id")
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset.order_by("-is_primary", "name")

    def perform_destroy(self, instance):
        """
        Soft delete - set is_active=False instead of actually deleting.
        """
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
