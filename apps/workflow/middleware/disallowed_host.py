"""Middleware to handle DisallowedHost exceptions gracefully."""

import logging

from django.core.exceptions import DisallowedHost
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class DisallowedHostMiddleware:
    """
    Middleware to catch DisallowedHost exceptions and return a clean 400 response.

    This prevents break-in attempts from filling logs with tracebacks while still
    rejecting the requests appropriately.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Handle DisallowedHost exceptions without traceback."""
        if isinstance(exception, DisallowedHost):
            # Extract IP from the exception message
            msg = str(exception)
            if "'" in msg:
                ip = msg.split("'")[1]
                logger.warning(f"Login attempt from unknown IP {ip}")
            else:
                logger.warning(f"Login attempt from unknown host: {msg}")

            # Return 400 Bad Request without traceback
            return HttpResponse("Bad Request", status=400)

        # Let other exceptions propagate normally
        return None
