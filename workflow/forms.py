# workflow/forms.py
import logging

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.db.models import Q

from workflow.models import (
    AdjustmentEntry,
    Client,
    Invoice,
    Job,
    JobPricing,
    MaterialEntry,
    Staff,
    TimeEntry,
)

logger = logging.getLogger(__name__)
DEBUG_FORM = False  # Toggle form debugging


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = "__all__"  # Include all fields from the model

    class JobForm(forms.ModelForm):
        class Meta:
            model = Job
            fields = "__all__"  # Include all fields from the model

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Ensure that the 'id' field is included as a hidden input
            self.fields["id"].widget = forms.HiddenInput()
            # Disable 'date_created' as read-only
            self.fields["date_created"].disabled = True
            if "last_updated" in self.fields:
                self.fields["last_updated"].disabled = True


class JobPricingForm(forms.ModelForm):
    class Meta:
        model = JobPricing
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["job"].disabled = True  # Make job read-only
        self.fields["pricing_stage"].disabled = True  # Make pricing_stage read-only


class MaterialEntryForm(forms.ModelForm):
    class Meta:
        model = MaterialEntry
        exclude = ["job_pricing"]


class AdjustmentEntryForm(forms.ModelForm):
    class Meta:
        model = AdjustmentEntry
        exclude = ["job_pricing"]


class TimeEntryForm(forms.ModelForm):
    class Meta:
        # Rate types to match with parsed types in timesheet_entry.js
        RATE_TYPE_CHOICES = [
            (1.0, "Ord"),
            (1.5, "Ovt"),
            (2.0, "Dt"),
            (0.0, "Unpaid"),
        ]

        model = TimeEntry

        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 3}
            ),  # Expand description field (with rows) for better readability
            "wage_rate_multiplier": forms.Select(
                choices=RATE_TYPE_CHOICES
            ),  # Dropdown for rate type selection
        }

        fields = (
            "staff",
            "date",
            "job_pricing",
            "hours",
            "wage_rate",
            "wage_rate_multiplier",
            "charge_out_rate",
            "is_billable",
            "description",
            "note",
        )

    def __init__(self, *args, staff_member=None, timesheet_date=None, **kwargs):
        """
        Form constructor. Main function is to prepopulate certain fields (such as the staff
        and its information, alongside with the date, which are all provided by the view)
        """
        super().__init__(*args, **kwargs)

        self.fields["staff"].initial = staff_member
        self.fields["staff"].widget = forms.HiddenInput()
        self.fields["staff"].required = False

        self.fields["date"].initial = timesheet_date
        self.fields["date"].widget = forms.HiddenInput()

        self.fields["job_pricing"].queryset = (
            JobPricing.objects.select_related("job")
            .filter(job__status__in=["quoting", "approved", "in_progress", "special"])
            .order_by("job__name")
        )
        self.fields["job_pricing"].required = True

        self.fields["wage_rate"].initial = staff_member.wage_rate
        self.fields["wage_rate"].widget = forms.HiddenInput()

        self.fields["wage_rate_multiplier"].initial = 1.0
        self.fields["wage_rate_multiplier"].help_text = (
            "Multiplier for hourly rate. "
            "Ord (1.0), Ovt (1.5), Dt (2.0), Unpaid (0.0)"
        )

        self.fields["charge_out_rate"].initial = 1.0
        self.fields["charge_out_rate"].widget = forms.HiddenInput()

    def save(self, commit=True):
        """
        Set charge_out_rate based on job_pricing before saving.
        Charge-out rates are managed via JobPricing and CompanyDefaults.
        Staff wage rates are set above for consistency, but charge-out rates depend on the job's context, as defined in JobPricing.
        """
        instance = super().save(commit=False)
        job_pricing = self.cleaned_data.get("job_pricing")

        if job_pricing:
            instance.charge_out_rate = job_pricing.job.charge_out_rate
        else:
            logger.error("Job Pricing is missing")
            raise ValueError("Job Pricing is required to set charge_out_rate")

        if commit:
            instance.save()

        return instance


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
            "raw_json",
        ]
        widgets = {
            "raw_json": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["raw_json"].widget.attrs["readonly"] = True
        self.fields["name"].required = True
        self.fields["name"].widget.attrs["required"] = "required"

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


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "number",
            "client",
            "date",
            "total_excl_tax",
            "status",
            "raw_json",
        ]
        widgets = {
            "raw_json": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["raw_json"].widget.attrs["readonly"] = True


class PaidAbsenceForm(forms.Form):
    LEAVE_CHOICES = [
        ("annual", "Annual Leave"),
        ("sick", "Sick Leave"),
        ("other", "Other Leave"),
    ]

    EXCLUDED_STAFF_IDS = [
        "a9bd99fa-c9fb-43e3-8b25-578c35b56fa6",
        "b50dd08a-58ce-4a6c-b41e-c3b71ed1d402",
        "d335acd4-800e-517a-8ff4-ba7aada58d14",
        "e61e2723-26e1-5d5a-bd42-bbd318ddef81",
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
            Q(id__in=EXCLUDED_STAFF_IDS)
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Staff Member",
        empty_label="Select a staff member",
        required=True,
    )
