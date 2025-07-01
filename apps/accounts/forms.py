from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from apps.accounts.models import Staff


class StaffCreationForm(UserCreationForm):
    """
    A form for creating new staff users with all required fields.
    Extends Django's UserCreationForm with custom validation and help text.
    """

    class Meta:
        model = Staff
        fields = (
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            "ims_payroll_id",
            "is_staff",
            "is_active",
        )

    # Override to provide more helpful error messages
    error_messages = {
        "password_mismatch": "The two password fields didn't match.",
        "password_too_short": "Password must be at least 10 characters.",
        "password_too_common": "Password can't be a commonly used password.",
        "password_entirely_numeric": "Password can't be entirely numeric.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = (
            "Your password must be at least 10 characters long, "
            "can't be too similar to your personal information, "
            "can't be a commonly used password, and "
            "can't be entirely numeric."
        )


class StaffChangeForm(UserChangeForm):
    """
    A form for updating staff users. Extends Django's UserChangeForm.
    Includes all editable fields from the Staff model.
    """

    class Meta:
        model = Staff
        fields = (
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            "ims_payroll_id",
            "is_staff",
            "is_active",
            "is_superuser",
            "groups",
            "user_permissions",
        )
