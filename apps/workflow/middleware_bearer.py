import logging
from typing import Callable

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)
User = get_user_model()


class BearerIdentityMiddleware:
    """
    Identity layer for bearer tokens.

    Non-blocking: attempts to authenticate from bearer token if configured,
    but never raises exceptions. Falls through to cookie auth if bearer fails.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not settings.ALLOW_BEARER_TOKEN_AUTHENTICATION:
            return self.get_response(request)

        if request.user.is_authenticated:
            return self.get_response(request)

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return self.get_response(request)

        token = auth_header[7:]

        try:
            payload = jwt.decode(
                token,
                settings.BEARER_TOKEN_SECRET,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )

            if payload.get("iss") != "dev":
                return self.get_response(request)

            user_id = payload.get("user_id")
            if not user_id:
                return self.get_response(request)

            user = User.objects.get(id=user_id)
            request.user = user
            request._cached_user = user

        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError, User.DoesNotExist):
            pass

        return self.get_response(request)
