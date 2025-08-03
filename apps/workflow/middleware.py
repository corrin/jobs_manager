import logging
from datetime import datetime
from typing import Callable

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.workflow.services.error_persistence import persist_app_error
from jobs_manager.authentication import JWTAuthentication

# Get access logger configured in Django settings
access_logger = logging.getLogger("access")


class AccessLoggingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Try to authenticate with JWT if not already authenticated
        if not request.user.is_authenticated:
            jwt_auth = JWTAuthentication()
            try:
                auth_result = jwt_auth.authenticate(request)
                if auth_result:
                    request.user, _ = auth_result
            except Exception:
                # If JWT authentication fails, continue with anonymous user
                pass

        # Handle unhappy case first - unauthenticated users
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Log authenticated user access
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user = getattr(request.user, "email", str(request.user))
            page = request.path
            method = request.method

            access_logger.info(f"{timestamp}\t{method}\t{user}\t{page}")
        except Exception as e:
            # Log any errors that occur during logging
            access_logger.error(f"Error logging access: {e}")
            persist_app_error(e)
        return self.get_response(request)


class LoginRequiredMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.exempt_urls = []
        self.exempt_url_prefixes = []

        if hasattr(settings, "LOGIN_EXEMPT_URLS"):
            for url_name in settings.LOGIN_EXEMPT_URLS:
                # Add support for Xero endpoints with dynamic UUIDs
                if (
                    url_name.startswith("api/xero/create_invoice/")
                    or url_name.startswith("api/xero/create_quote/")
                    or url_name.startswith("api/xero/delete_invoice/")
                    or url_name.startswith("api/xero/delete_quote/")
                ):
                    self.exempt_url_prefixes.append(url_name)
                    continue
                try:
                    # Try to resolve the URL name to an actual path
                    self.exempt_urls.append(reverse(url_name))
                except Exception:
                    # If it fails, we assume it's a prefix and add it directly
                    self.exempt_url_prefixes.append(url_name)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # In DEBUG mode, skip login requirements but continue processing
        if settings.DEBUG:
            # Don't enforce login requirements, continue middleware chain
            return self.get_response(request)

        login_path = reverse("accounts:login")
        # Allow POST requests to login endpoint
        login_path = reverse("accounts:login").rstrip("/")
        req_path = request.path_info.rstrip("/")
        if request.method == "POST" and req_path == login_path:
            return self.get_response(request)
        # Check exact path matches first
        if request.path_info in self.exempt_urls:
            return self.get_response(request)  # Check path prefixes
        path = request.path_info.lstrip("/")
        if any(path.startswith(prefix) for prefix in self.exempt_url_prefixes):
            return self.get_response(request)

        # Handle logout endpoints specifically
        if request.path_info.endswith("/logout/"):
            return self.get_response(request)

        if not request.user.is_authenticated:
            if request.path_info.startswith("/api/"):
                return JsonResponse(
                    {"detail": "Authentication credentials were not provided."},
                    status=401,
                )
            accepts_json = (
                request.headers.get("Accept", "").lower().startswith("application/json")
            )
            is_json = (
                request.headers.get("Content-Type", "")
                .lower()
                .startswith("application/json")
            )
            if accepts_json or is_json:
                return JsonResponse(
                    {"detail": "Authentication credentials were not provided."},
                    status=401,
                )
            # Always redirect to the front-end SPA login
            frontend_login_url = getattr(settings, "FRONT_END_URL", None)
            if frontend_login_url:
                return redirect(frontend_login_url.rstrip("/") + "/login")
            # If FRONT_END_URL is not set, return 401 to avoid redirect loop
            return JsonResponse(
                {"detail": "Authentication required. FRONT_END_URL not set."},
                status=401,
            )
        return self.get_response(request)


class PasswordStrengthMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if getattr(settings, "ENABLE_JWT_AUTH", False) and not hasattr(
            request, "session"
        ):
            return self.get_response(request)

        if request.user.is_authenticated and request.user.password_needs_reset:
            exempt_urls = [
                reverse("accounts:password_change"),
                reverse("accounts:password_change_done"),
                reverse("accounts:logout"),
                reverse("accounts:token_obtain_pair"),
                reverse("accounts:token_refresh"),
                reverse("accounts:token_verify"),
            ]

            if request.path not in exempt_urls and not request.path.startswith(
                "/static/"
            ):
                messages.warning(
                    request,
                    "For security reasons, you need to update your password to "
                    "meet our new requirements.",
                )
                return redirect("accounts:password_change")

        return self.get_response(request)
