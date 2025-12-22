from typing import TYPE_CHECKING

from django.http import HttpRequest
from rest_framework.permissions import BasePermission

if TYPE_CHECKING:
    from rest_framework.views import APIView


class IsStaff(BasePermission):
    def has_permission(self, request: HttpRequest, view: "APIView") -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_office_staff
        )
