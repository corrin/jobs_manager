from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workflow.serializers import CompanyDefaultsSerializer
from apps.workflow.services.company_defaults_service import get_company_defaults


class CompanyDefaultsAPIView(APIView):
    """
    API view for managing company default settings.

    This view provides endpoints to retrieve and update the company's default
    configuration settings. Only admin users are permitted to access these endpoints.

    Endpoints:
        GET: Retrieve current company defaults
        PUT: Update all company defaults (full update)
        PATCH: Partially update company defaults

    Permissions:
        - IsAdminUser: Only admin users can access this API

    Returns:
        Company defaults data serialized using CompanyDefaultsSerializer
    """

    permission_classes = [IsAdminUser]
    serializer_class = CompanyDefaultsSerializer

    def get(self, request):
        instance = get_company_defaults()
        serializer = CompanyDefaultsSerializer(instance)
        return Response(serializer.data)

    def put(self, request):
        instance = get_company_defaults()
        serializer = CompanyDefaultsSerializer(
            instance, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        instance = get_company_defaults()
        serializer = CompanyDefaultsSerializer(
            instance, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
