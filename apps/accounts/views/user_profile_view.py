"""
User profile views for JWT authentication
"""

from django.conf import settings
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import UserProfileSerializer


class GetCurrentUserAPIView(APIView):
    """
    Get current authenticated user information via JWT from httpOnly cookie
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    @extend_schema(
        summary="Returns the current authenticated user profile",
        responses={200: UserProfileSerializer},
    )
    def get(self, request: Request) -> Response:
        try:
            user = request.user
            serializer = UserProfileSerializer(user, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Error retrieving user profile: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutUserAPIView(APIView):
    """
    Custom logout view that clears JWT httpOnly cookies
    """

    permission_classes = []  # No authentication required for logout

    @extend_schema(
        summary="Logs out the current user by clearing JWT cookies",
        request=None,
        responses={200: OpenApiTypes.OBJECT, 500: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request) -> Response:
        try:
            simple_jwt_settings = getattr(settings, "SIMPLE_JWT", {})

            response = Response(
                {"success": True, "message": "Successfully logged out"},
                status=status.HTTP_200_OK,
            )

            # Clear access token cookie
            access_cookie_name = simple_jwt_settings.get("AUTH_COOKIE", "access_token")
            response.delete_cookie(
                access_cookie_name,
                domain=simple_jwt_settings.get("AUTH_COOKIE_DOMAIN"),
                samesite=simple_jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
            )

            # Clear refresh token cookie
            refresh_cookie_name = simple_jwt_settings.get(
                "REFRESH_COOKIE", "refresh_token"
            )
            response.delete_cookie(
                refresh_cookie_name,
                domain=simple_jwt_settings.get("AUTH_COOKIE_DOMAIN"),
                samesite=simple_jwt_settings.get("REFRESH_COOKIE_SAMESITE", "Lax"),
            )

            return response

        except Exception as e:
            return Response(
                {"error": f"Error during logout: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
