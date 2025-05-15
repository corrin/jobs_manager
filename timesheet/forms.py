from decimal import Decimal

from django import forms
from django.db.models import Q

from accounts.models import Staff
from accounts.utils import get_excluded_staff

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
        queryset=Staff.objects.filter(is_active=True, is_staff=False).exclude(
            Q(id__in=get_excluded_staff())
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Staff Member",
        empty_label="Select a staff member",
        required=True,
    )