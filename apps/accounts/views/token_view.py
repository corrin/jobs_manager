import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import CustomTokenObtainPairSerializer

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Customized token obtain view that handles password reset requirement
    and sets JWT tokens as httpOnly cookies
    """

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        logger.info(
            "CustomTokenObtainPairView POST called with username: %s",
            request.data.get("username"),
        )
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            User = get_user_model()

            try:
                username = request.data.get("username")
                if username:
                    user = User.objects.get(email=username)
                    logger.debug("User %s found", username)

                    if (
                        hasattr(user, "password_needs_reset")
                        and user.password_needs_reset
                    ):
                        logger.info("User %s needs password reset", username)
                        response.data["password_needs_reset"] = True
                        response.data["password_reset_url"] = (
                            request.build_absolute_uri(
                                reverse("accounts:password_change")
                            )
                        )

                    if getattr(settings, "ENABLE_JWT_AUTH", False):
                        logger.info("Setting JWT cookies for user %s", username)
                        self._set_jwt_cookies(response, response.data)

            except User.DoesNotExist:
                logger.warning("User %s does not exist", username)

        else:
            logger.warning(
                "Token obtain failed with status code: %s", response.status_code
            )

        return response

    def _set_jwt_cookies(self, response: Response, data: dict) -> None:
        """Set JWT tokens as httpOnly cookies"""
        import os

        simple_jwt_settings = getattr(settings, "SIMPLE_JWT", {})
        env_samesite = os.getenv("COOKIE_SAMESITE")
        settings_samesite = simple_jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax")

        if env_samesite:
            env_samesite = env_samesite.capitalize()

        if env_samesite and env_samesite != settings_samesite:
            samesite_value = env_samesite
        else:
            samesite_value = settings_samesite

        # Set access token cookie
        if "access" in data:
            logger.debug("Setting access token cookie")
            response.set_cookie(
                simple_jwt_settings.get("AUTH_COOKIE", "access_token"),
                data["access"],
                max_age=simple_jwt_settings.get(
                    "ACCESS_TOKEN_LIFETIME"
                ).total_seconds(),
                httponly=simple_jwt_settings.get("AUTH_COOKIE_HTTP_ONLY", True),
                secure=simple_jwt_settings.get("AUTH_COOKIE_SECURE", True),
                samesite=samesite_value,
                domain=simple_jwt_settings.get("AUTH_COOKIE_DOMAIN"),
            )
            del data["access"]

        # Set refresh token cookie
        if "refresh" in data:
            logger.debug("Setting refresh token cookie")
            response.set_cookie(
                simple_jwt_settings.get("REFRESH_COOKIE", "refresh_token"),
                data["refresh"],
                max_age=simple_jwt_settings.get(
                    "REFRESH_TOKEN_LIFETIME"
                ).total_seconds(),
                httponly=simple_jwt_settings.get("REFRESH_COOKIE_HTTP_ONLY", True),
                secure=simple_jwt_settings.get("REFRESH_COOKIE_SECURE", True),
                samesite=samesite_value,
                domain=simple_jwt_settings.get("AUTH_COOKIE_DOMAIN"),
            )
            del data["refresh"]


class CustomTokenRefreshView(TokenRefreshView):
    """
    Customized token refresh view that uses httpOnly cookies
    """

    def post(self, request, *args, **kwargs):
        # Get refresh token from cookie if not in request data
        simple_jwt_settings = getattr(settings, "SIMPLE_JWT", {})
        refresh_cookie_name = simple_jwt_settings.get("REFRESH_COOKIE", "refresh_token")

        if "refresh" not in request.data and refresh_cookie_name in request.COOKIES:
            # Create mutable copy of request data
            request_data = request.data.copy()
            request_data["refresh"] = request.COOKIES[refresh_cookie_name]
            request._full_data = request_data

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            # Set new access token as httpOnly cookie
            if getattr(settings, "ENABLE_JWT_AUTH", False):
                self._set_access_cookie(response, response.data)

        return response

    def _set_access_cookie(self, response: Response, data: dict) -> None:
        """Set access token as httpOnly cookie"""
        simple_jwt_settings = getattr(settings, "SIMPLE_JWT", {})

        if "access" in data:
            response.set_cookie(
                simple_jwt_settings.get("AUTH_COOKIE", "access_token"),
                data["access"],
                max_age=simple_jwt_settings.get(
                    "ACCESS_TOKEN_LIFETIME"
                ).total_seconds(),
                httponly=simple_jwt_settings.get("AUTH_COOKIE_HTTP_ONLY", True),
                secure=simple_jwt_settings.get("AUTH_COOKIE_SECURE", True),
                samesite=simple_jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
                domain=simple_jwt_settings.get("AUTH_COOKIE_DOMAIN"),
            )
            # Remove access token from response data for security
            del data["access"]
