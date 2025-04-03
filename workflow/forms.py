# workflow/forms.py
import logging

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from workflow.models import (
    AdjustmentEntry,
    Client,
    Job,
    JobPricing,
    MaterialEntry,
    Staff,
    TimeEntry,
    PurchaseOrder,
    PurchaseOrderLine,
)
from workflow.utils import get_excluded_staff

logger = logging.getLogger(__name__)
DEBUG_FORM = False  # Toggle form debugging




class StaffCreationForm(UserCreationForm):
    class Meta:
        model = Staff
        fields = (
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            # "charge_out_rate",
            "ims_payroll_id",
            "is_staff",
            "is_active",
        )
    
    # Override to provide more helpful error messages
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
        'password_too_short': _("Password must be at least 10 characters."),
        'password_too_common': _("Password can't be a commonly used password."),
        'password_entirely_numeric': _("Password can't be entirely numeric."),
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = _(
            "Your password must be at least 10 characters long, "
            "can't be too similar to your personal information, "
            "can't be a commonly used password, and "
            "can't be entirely numeric."
        )


class StaffChangeForm(UserChangeForm):
    class Meta:
        model = Staff
        fields = (
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            # "charge_out_rate",
            "ims_payroll_id",
            "is_staff",
            "is_active",
            "is_superuser",
            "groups",
            "user_permissions",
        )


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "name",
            "email",
            "phone",
            "address",
            "is_account_customer",
            "xero_contact_id",
            "raw_json",
        ]
        widgets = {
            "raw_json": forms.HiddenInput(),
            "xero_contact_id": forms.TextInput(attrs={"readonly": "readonly"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["raw_json"].widget.attrs["readonly"] = True
        self.fields["name"].required = True
        self.fields["name"].widget.attrs["required"] = "required"
        self.fields["xero_contact_id"].required = False
        self.fields["xero_contact_id"].widget.attrs["readonly"] = True

        if DEBUG_FORM:
            logger.debug(
                "ClientForm init - args: %(args)s, kwargs: %(kwargs)s",
                {
                    "args": args,
                    "kwargs": kwargs,
                },
            )
            logger.debug(
                "ClientForm instance: %(instance)s",
                {"instance": self.instance.__dict__},
            )

            for field_name, field in self.fields.items():
                logger.debug(
                    "Field %(name)s: initial=%(initial)s, value=%(value)s",
                    {
                        "name": field_name,
                        "initial": field.initial,
                        "value": self.initial.get(field_name),
                    },
                )

    def clean(self):
        cleaned_data = super().clean()
        # logger.debug(f"ClientForm cleaned data: {cleaned_data}")
        return cleaned_data


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


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'po_number', 'reference', 'order_date', 'expected_delivery']
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery': forms.DateInput(attrs={'type': 'date'}),
        }


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ['job', 'description', 'quantity', 'unit_cost', 'price_tbc']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price_tbc': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        price_tbc = cleaned_data.get('price_tbc')
        unit_cost = cleaned_data.get('unit_cost')
        
        if price_tbc:
            # If price_tbc is True, set unit_cost to None
            cleaned_data['unit_cost'] = None
        elif unit_cost is None:
            # If price_tbc is False, unit_cost cannot be None
            self.add_error('unit_cost', 'Unit cost is required when price is not TBC')
            
        return cleaned_data
