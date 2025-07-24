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
        # Extract data from 'body' wrapper if it exists (Zodios sends data wrapped in 'body')
        request_data = (
            request.data.get("body", request.data)
            if isinstance(request.data, dict) and "body" in request.data
            else request.data
        )

        instance = get_company_defaults()
        serializer = CompanyDefaultsSerializer(
            instance, data=request_data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        print(f"DEBUG: PATCH request received with data = {request.data}")

        # Extract data from 'body' wrapper if it exists (Zodios sends data wrapped in 'body')
        request_data = (
            request.data.get("body", request.data)
            if isinstance(request.data, dict) and "body" in request.data
            else request.data
        )
        print(f"DEBUG: Extracted request_data = {request_data}")

        instance = get_company_defaults()
        print(f"DEBUG: Current instance shop_client_name = {instance.shop_client_name}")
        serializer = CompanyDefaultsSerializer(
            instance, data=request_data, partial=True, context={"request": request}
        )
        print(f"DEBUG: Serializer created, calling is_valid()")
        serializer.is_valid(raise_exception=True)
        print(
            f"DEBUG: Serializer is valid, validated_data = {serializer.validated_data}"
        )
        print(f"DEBUG: Calling serializer.save()")
        result = serializer.save()
        print(
            f"DEBUG: serializer.save() returned, shop_client_name = {result.shop_client_name}"
        )
        return Response(serializer.data)
