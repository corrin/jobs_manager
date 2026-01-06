from rest_framework.permissions import BasePermission

from apps.accounts.models import Staff


class IsOfficeStaff(BasePermission):
    """
    Custom permission to only allow office staffs to proceed with requests
    """

    def has_permission(self, request, view):
        if request.user.is_office_staff:
            return True

        return False


class IsStaffUser(BasePermission):
    """
    Custom permission to allow any authenticated staff user (office or workshop).
    """

    def has_permission(self, request, view):
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return False

        return isinstance(user, Staff)
