from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workflow.serializers import CompanyDefaultsSerializer
from apps.workflow.services.company_defaults_service import get_company_defaults


class CompanyDefaultsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        instance = get_company_defaults()
        serializer = CompanyDefaultsSerializer(instance)
        return Response(serializer.data)

    def put(self, request):
        instance = get_company_defaults()
        serializer = CompanyDefaultsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        instance = get_company_defaults()
        serializer = CompanyDefaultsSerializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
