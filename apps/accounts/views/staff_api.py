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
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Staff.objects.all()


class StaffRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated, IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Staff.objects.all()

    def update(self, request, *args, **kwargs):
        logger = logging.getLogger("workflow")
        staff_id = kwargs.get("pk")
        logger.info(f"[StaffUpdate] Método: {request.method} | Staff ID: {staff_id}")
        logger.info(f"[StaffUpdate] Dados recebidos: {request.data}")
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            logger.error(f"[StaffUpdate] Erros de validação: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        logger.info(
            f"[StaffUpdate] Atualização realizada com sucesso para Staff ID: {staff_id}"
        )
        return Response(serializer.data)
