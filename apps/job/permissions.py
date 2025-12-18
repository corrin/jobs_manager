from rest_framework.permissions import BasePermission


class IsOfficeStaff(BasePermission):
    """
    Custom permission to only allow office staffs to proceed with requests
    """

    def has_permission(self, request, view):
        if request.user.is_office_staff:
            return True
        
        return False
