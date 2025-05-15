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
    TimeEntry,
    PurchaseOrder,
    PurchaseOrderLine,
)
from accounts.utils import get_excluded_staff

from accounts.models import Staff

logger = logging.getLogger(__name__)
DEBUG_FORM = False  # Toggle form debugging


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
