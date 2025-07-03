from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest, HttpResponse
from simple_history.admin import SimpleHistoryAdmin

from apps.accounts.forms import StaffChangeForm, StaffCreationForm
from apps.accounts.models import Staff


@admin.register(Staff)
class StaffAdmin(UserAdmin, SimpleHistoryAdmin):
    add_form = StaffCreationForm
    form = StaffChangeForm
    model = Staff

    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "is_staff",
        "is_active",
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal Info",
            {
                "fields": (
                    "icon",
                    "first_name",
                    "last_name",
                    "preferred_name",
                    "wage_rate",
                    "ims_payroll_id",
                )
            },
        ),
        (
            "Working Hours",
            {
                "fields": (
                    "hours_mon",
                    "hours_tue",
                    "hours_wed",
                    "hours_thu",
                    "hours_fri",
                    "hours_sat",
                    "hours_sun",
                ),
                "description": "Set standard working hours for each day of the week. "
                "Use 0 for non-working days.",
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "preferred_name",
                    "wage_rate",
                    "ims_payroll_id",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    def user_change_password(self, request: HttpRequest, id: str, form_url: str = "") -> HttpResponse:
        """
        Display the password change form for a specific user.
        
        This Django admin view handles password changes for individual users
        in the admin interface. It displays a form allowing administrators
        to set a new password for the selected user.
        
        Args:
            request: The HTTP request object
            id: The user ID whose password will be changed
            form_url: Optional form URL for the password change form
            
        Returns:
            HttpResponse containing the password change form or redirect after success
        """
        return super().user_change_password(request, id, form_url)

    def history_form_view(self, request: HttpRequest, object_id: str, version_id: str) -> HttpResponse:
        """
        Display the historical form view for a specific object version.
        
        This view is provided by SimpleHistoryAdmin and shows a read-only form
        displaying the state of an object at a specific point in history.
        Used for viewing historical changes to Staff records.
        
        Args:
            request: The HTTP request object
            object_id: The ID of the staff object
            version_id: The ID of the specific historical version
            
        Returns:
            HttpResponse containing the historical form view
        """
        return super().history_form_view(request, object_id, version_id)
