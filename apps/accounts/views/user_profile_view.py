"""
User profile views for JWT authentication
"""

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.serializers import UserProfileSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Get current authenticated user information via JWT from httpOnly cookie
    """
    try:
        user = request.user
        serializer = UserProfileSerializer(user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error retrieving user profile: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def logout_user(request):
    """
    Custom logout view that clears JWT httpOnly cookies
    """
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
        refresh_cookie_name = simple_jwt_settings.get("REFRESH_COOKIE", "refresh_token")
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
