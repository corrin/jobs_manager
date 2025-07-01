# purchasing/forms.py
import logging

from django import forms

from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine

logger = logging.getLogger(__name__)
DEBUG_FORM = False  # Toggle form debugging


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "supplier",
            "po_number",
            "reference",
            "order_date",
            "expected_delivery",
        ]
        widgets = {
            "order_date": forms.DateInput(attrs={"type": "date"}),
            "expected_delivery": forms.DateInput(attrs={"type": "date"}),
        }


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ["job", "description", "quantity", "unit_cost", "price_tbc"]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "unit_cost": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "price_tbc": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        price_tbc = cleaned_data.get("price_tbc")
        unit_cost = cleaned_data.get("unit_cost")

        if price_tbc:
            # If price_tbc is True, set unit_cost to None
            cleaned_data["unit_cost"] = None
        elif unit_cost is None:
            # If price_tbc is False, unit_cost cannot be None
            self.add_error("unit_cost", "Unit cost is required when price is not TBC")

        return cleaned_data
