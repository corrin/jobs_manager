from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest


def debug_mode(request: HttpRequest) -> Dict[str, Any]:
    return {"DEBUG_MODE": settings.DEBUG}
