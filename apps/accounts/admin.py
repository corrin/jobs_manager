from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
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
