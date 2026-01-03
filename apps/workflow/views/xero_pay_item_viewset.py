from rest_framework import permissions, viewsets

from apps.workflow.models import XeroPayItem
from apps.workflow.serializers import XeroPayItemSerializer


class XeroPayItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Xero pay items (earnings rates and leave types).

    Read-only - these are synced from Xero, not created locally.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = XeroPayItemSerializer
    queryset = XeroPayItem.objects.all()
