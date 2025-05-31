# workflow/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin

from workflow.models import CompanyDefaults
from workflow.models.ai_provider import AIProvider


class AIProviderInline(admin.TabularInline):
    """Inline admin for AIProvider to allow adding multiple providers in CompanyDefaults."""
    model = AIProvider
    extra = 1
    fields = ('name', 'provider_type', 'api_key', 'active')

    def save_model(self, request, obj, form, change):
        """Ensure only one provider is active by deactivating others when a new one is activated."""
        if obj.active:
            AIProvider.objects.filter(
                company=obj.company,
                active=True
            ).exclude(pk=obj.pk).update(active=False)
        super().save_model(request, obj, form, change)


@admin.register(CompanyDefaults)
class CompanyDefaultsAdmin(admin.ModelAdmin):
    def edit_link(self, obj):
        from django.utils.html import format_html
        return format_html('<a href="{}/change/">Edit defaults</a>', obj.pk)
    
    edit_link.short_description = 'Actions'
    edit_link.allow_tags = True

    list_display = ["edit_link", "charge_out_rate", "wage_rate", "time_markup", "materials_markup", "starting_job_number"]
    inlines = [AIProviderInline]

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
                    "starting_po_number",
                    "po_prefix"
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
            }
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
            "Quote Templates",
            {
                "fields": (
                    "master_quote_template_url",
                ),
                "description": "URL to the master Google Sheets quote template that will be duplicated for new quotes.",
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
            "(DEPRECATED) LLM Integration",
            {
                "fields": (
                    "anthropic_api_key",
                    "gemini_api_key"
                ),
                "description": "API keys for Large Language Model integrations.",
            },
        ),
        (
            "AI Providers",
            {
                "fields": (),
                "description": "LLM providers are managed in the section below. Only one provider can be active at a time.",
            }
        )
    )
