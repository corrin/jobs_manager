from django import forms
from django.db.models import Q

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff


class PaidAbsenceForm(forms.Form):
    LEAVE_CHOICES = [
        ("annual", "Annual Leave"),
        ("sick", "Sick Leave"),
        ("other", "Other Leave"),
    ]

    leave_type = forms.ChoiceField(
        choices=LEAVE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Leave Type",
    )

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Start Date",
    )

    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="End Date",
    )

    staff = forms.ModelChoiceField(
        queryset=Staff.objects.none(),  # Will be set in __init__
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Staff Member",
        empty_label="Select a staff member",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["staff"].queryset = Staff.objects.filter(
            is_active=True, is_staff=False
        ).exclude(Q(id__in=get_excluded_staff()))
