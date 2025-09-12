# workflow/admin.py


from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest

from apps.workflow.models import AIProvider, CompanyDefaults


@admin.register(AIProvider)
class AIProviderAdmin(admin.ModelAdmin):
    """Admin interface for AIProvider."""

    list_display = ("name", "provider_type", "model_name", "default")
    list_filter = ("provider_type", "default")
    search_fields = ("name", "provider_type", "model_name")
    fields = ("name", "provider_type", "model_name", "api_key", "default")

    def save_model(
        self, request: HttpRequest, obj: AIProvider, form: ModelForm, change: bool
    ) -> None:
        """Ensure only one provider is default by deactivating others when a new one is set as default."""
        if obj.default:
            AIProvider.objects.filter(default=True).exclude(pk=obj.pk).update(
                default=False
            )
        super().save_model(request, obj, form, change)


@admin.register(CompanyDefaults)
class CompanyDefaultsAdmin(admin.ModelAdmin):
    def edit_link(self, obj: CompanyDefaults) -> str:
        """
        Generate an edit link for the CompanyDefaults object.

        Creates a clickable "Edit defaults" link in the admin list view
        that navigates to the change form for the company defaults.
        """
        from django.utils.html import format_html

        return format_html('<a href="{}/change/">Edit defaults</a>', obj.pk)

    edit_link.short_description = "Actions"
    edit_link.allow_tags = True

    list_display = [
        "edit_link",
        "charge_out_rate",
        "wage_rate",
        "time_markup",
        "materials_markup",
        "starting_job_number",
    ]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "time_markup",
                    "materials_markup",
                    "charge_out_rate",
                    "wage_rate",
                    "starting_job_number",
                )
            },
        ),
        (
            "Thresholds",
            {
                "fields": (
                    "billable_threshold_green",
                    "billable_threshold_amber",
                    "daily_gp_target",
                    "shop_hours_target_percentage",
                )
            },
        ),
        (
            "Working Hours",
            {
                "fields": (
                    ("mon_start", "mon_end"),
                    ("tue_start", "tue_end"),
                    ("wed_start", "wed_end"),
                    ("thu_start", "thu_end"),
                    ("fri_start", "fri_end"),
                )
            },
        ),
        (
            "Google Sheets Integration (for Job Quotes)",
            {
                "fields": (
                    "master_quote_template_url",
                    "master_quote_template_id",
                    "gdrive_quotes_folder_url",
                    "gdrive_quotes_folder_id",
                ),
                "description": "These fields are used to configure the Google Sheets integration for job quotes. The master template is used to generate new quotes, and the folder is where all quotes are stored.",
            },
        ),
        (
            "Xero Integration",
            {
                "fields": (
                    "xero_tenant_id",
                    "last_xero_sync",
                    "last_xero_deep_sync",
                ),
                "description": "To force a deep sync, clear the 'last_xero_deep_sync' field or set it to a date more than 30 days ago.",
            },
        ),
        (
            "AI Providers",
            {
                "fields": (),
                "description": "LLM providers are managed separately in the AI Providers admin section. Only one provider can be default at a time.",
            },
        ),
    )
