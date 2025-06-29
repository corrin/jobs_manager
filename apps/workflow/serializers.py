from rest_framework import serializers

from apps.workflow.models.ai_provider import AIProvider
from apps.workflow.models.app_error import AppError, XeroError
from apps.workflow.models.company_defaults import CompanyDefaults


class AIProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIProvider
        fields = [
            "id",
            "name",
            "provider_type",
            "model_name",
            "api_key",
            "default",
        ]


class CompanyDefaultsSerializer(serializers.ModelSerializer):
    ai_providers = AIProviderSerializer(many=True)
    company_name = serializers.CharField(read_only=True)

    class Meta:
        model = CompanyDefaults
        fields = [
            "company_name",
            "time_markup",
            "materials_markup",
            "charge_out_rate",
            "wage_rate",
            "starting_job_number",
            "starting_po_number",
            "po_prefix",
            "master_quote_template_url",
            "master_quote_template_id",
            "gdrive_quotes_folder_url",
            "gdrive_quotes_folder_id",
            "xero_tenant_id",
            "mon_start",
            "mon_end",
            "tue_start",
            "tue_end",
            "wed_start",
            "wed_end",
            "thu_start",
            "thu_end",
            "fri_start",
            "fri_end",
            "created_at",
            "updated_at",
            "last_xero_sync",
            "last_xero_deep_sync",
            "shop_client_name",
            "billable_threshold_green",
            "billable_threshold_amber",
            "daily_gp_target",
            "shop_hours_target_percentage",
            "ai_providers",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_ai_providers(self, value):
        default_count = sum(1 for provider in value if provider.get("default"))
        if default_count > 1:
            raise serializers.ValidationError(
                "Only one AIProvider can be set as default."
            )
        return value

    def update(self, instance, validated_data):
        ai_providers_data = validated_data.pop("ai_providers", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if ai_providers_data is not None:
            self._update_ai_providers(instance, ai_providers_data)
        return instance

    def _update_ai_providers(self, company_defaults, ai_providers_data):
        existing_ids = [item.get("id") for item in ai_providers_data if item.get("id")]
        # Delete removed providers
        AIProvider.objects.filter(company=company_defaults).exclude(
            id__in=existing_ids
        ).delete()
        for provider_data in ai_providers_data:
            provider_id = provider_data.get("id")
            if provider_id:
                provider = AIProvider.objects.get(
                    id=provider_id, company=company_defaults
                )
                for attr, value in provider_data.items():
                    setattr(provider, attr, value)
                provider.save()
            else:
                AIProvider.objects.create(company=company_defaults, **provider_data)


class AppErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppError
        fields = ["id", "timestamp", "message", "data"]


class XeroErrorSerializer(AppErrorSerializer):
    class Meta(AppErrorSerializer.Meta):
        model = XeroError
        fields = AppErrorSerializer.Meta.fields + ["entity", "reference_id", "kind"]
