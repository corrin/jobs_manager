import logging

from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Staff
from apps.accounts.permissions import IsStaff
from apps.accounts.serializers import StaffSerializer

logger = logging.getLogger(__name__)


class StaffListCreateAPIView(generics.ListCreateAPIView):
    """API endpoint for listing and creating staff members.

    Supports both GET (list all staff) and POST (create new staff) operations.
    Requires authentication and staff permissions. Handles multipart/form data
    for file uploads (e.g., profile pictures).
    """

    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Staff.objects.all()


class StaffRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """API endpoint for retrieving, updating, and deleting individual staff members.

    Supports GET (retrieve), PUT/PATCH (update), and DELETE operations on
    specific staff members. Includes comprehensive logging for update operations
    and handles multipart/form data for file uploads.
    """

    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Staff.objects.all()

    def update(self, request, *args, **kwargs):
        logger = logging.getLogger("workflow")
        staff_id = kwargs.get("pk")
        logger.info(f"[StaffUpdate] Method: {request.method} | Staff ID: {staff_id}")
        logger.info(f"[StaffUpdate] Received data: {request.data}")
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            logger.error(f"[StaffUpdate] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        logger.info(f"[StaffUpdate] Successfully updated Staff ID: {staff_id}")
        return Response(serializer.data)
