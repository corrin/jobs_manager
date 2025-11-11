import logging
from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import (
    BearerTokenRequestSerializer,
    BearerTokenResponseSerializer,
    EmptySerializer,
)
from apps.accounts.views.token_view import get_client_ip

logger = logging.getLogger(__name__)


@extend_schema(
    request=BearerTokenRequestSerializer,
    responses={
        200: BearerTokenResponseSerializer,
        401: EmptySerializer,
        403: EmptySerializer,
    },
    description="Generate bearer token. Only enabled when ALLOW_BEARER_TOKEN_AUTHENTICATION=True.",
)
class BearerTokenView(APIView):
    """
    Generate bearer tokens.

    Only works when ALLOW_BEARER_TOKEN_AUTHENTICATION=True.
    """

    permission_classes = []
    authentication_classes = []
    serializer_class = BearerTokenRequestSerializer

    def post(self, request):
        if not settings.ALLOW_BEARER_TOKEN_AUTHENTICATION:
            return Response(
                {"detail": "Bearer tokens are disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        username = request.data.get("username")
        password = request.data.get("password")
        client_ip = get_client_ip(request)

        if not username or not password:
            return Response(
                {"detail": "Username and password required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)

        if not user:
            logger.warning(
                "BEARER TOKEN LOGIN FAILURE - username=%s ip=%s",
                username,
                client_ip,
            )
            return Response(
                {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
            )

        exp_time = datetime.utcnow() + timedelta(minutes=15)

        payload = {
            "user_id": str(user.id),
            "iss": "dev",
            "exp": exp_time,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, settings.BEARER_TOKEN_SECRET, algorithm="HS256")

        logger.info(
            "BEARER TOKEN LOGIN SUCCESS - username=%s ip=%s",
            user.email,
            client_ip,
        )

        return Response({"token": token}, status=status.HTTP_200_OK)
