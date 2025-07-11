from rest_framework import serializers

# Existing models used in this serializer module
from .models import (
    AIProvider,
    AppError,
    CompanyDefaults,
    XeroAccount,
    XeroError,
    XeroToken,
)


class XeroTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = XeroToken
        fields = "__all__"


class AIProviderSerializer(serializers.ModelSerializer):
    """
    Serializer for reading AIProvider instances.
    This serializer is read-only and excludes the `api_key` for security.
    """

    class Meta:
        model = AIProvider
        fields = (
            "id",
            "name",
            "provider_type",
            "model_name",
            "default",
        )


class CompanyDefaultsSerializer(serializers.ModelSerializer):
    ai_providers = AIProviderSerializer(many=True, read_only=True)

    class Meta:
        model = CompanyDefaults
        fields = "__all__"

    def update(self, instance, validated_data):
        # Handle ai_providers from request data since it's read_only in the serializer
        request = self.context.get("request") if self.context else None

        if request and hasattr(request, "data"):
            ai_providers_data = request.data.get("ai_providers")
            if ai_providers_data is not None:
                self._update_ai_providers(instance, ai_providers_data)

        # Update the rest of the fields
        return super().update(instance, validated_data)

    def _update_ai_providers(self, instance, ai_providers_data):
        """
        Update the AI providers for this company.
        This will update existing providers and create new ones as needed.
        """
        existing_providers = {p.id: p for p in instance.ai_providers.all()}
        updated_provider_ids = set()

        # Process each provider in the request
        for provider_data in ai_providers_data:
            provider_id = provider_data.get("id")

            if provider_id and provider_id in existing_providers:
                # Update existing provider
                provider = existing_providers[provider_id]

                # Update fields
                provider.name = provider_data.get("name", provider.name)
                provider.provider_type = provider_data.get(
                    "provider_type", provider.provider_type
                )
                provider.model_name = provider_data.get(
                    "model_name", provider.model_name
                )
                provider.default = provider_data.get("default", provider.default)

                # Only update api_key if provided (not empty)
                api_key = provider_data.get("api_key")
                if api_key:
                    provider.api_key = api_key

                provider.save()
                updated_provider_ids.add(provider_id)
            else:
                # Create new provider
                new_provider = AIProvider.objects.create(
                    company=instance,
                    name=provider_data.get("name", ""),
                    provider_type=provider_data.get("provider_type", "openai"),
                    model_name=provider_data.get("model_name", ""),
                    api_key=provider_data.get("api_key", ""),
                    default=provider_data.get("default", False),
                )

        # Delete providers that weren't in the update list
        providers_to_delete = set(existing_providers.keys()) - updated_provider_ids
        if providers_to_delete:
            AIProvider.objects.filter(id__in=providers_to_delete).delete()


class XeroAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = XeroAccount
        fields = "__all__"


class AIProviderCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating AIProvider instances.
    This serializer handles the `api_key` securely by making it write-only.
    """

    # Make api_key write-only for security. It can be provided on create/update,
    # but it will never be included in a response.
    api_key = serializers.CharField(
        write_only=True,
        required=False,  # Not required on update, but validated below for create.
        allow_blank=True,
        style={"input_type": "password"},
        help_text="API Key for the provider. Leave blank to keep unchanged on update.",
    )

    class Meta:
        model = AIProvider
        fields = (
            "id",
            "name",
            "provider_type",
            "model_name",
            "default",
            "api_key",
            "company",  # Included to be set as read_only
        )
        read_only_fields = ("id", "company")

    def validate(self, data):
        """
        Validate that a new provider has an API key.
        """
        # On create (when instance is not present), api_key is required.
        if not self.instance and not data.get("api_key"):
            raise serializers.ValidationError(
                {"api_key": "API key is required for a new provider."}
            )
        return data


# ---------------------------------------------------------------------------
# Xero Error Serializers
# ---------------------------------------------------------------------------


class XeroErrorSerializer(serializers.ModelSerializer):
    """
    Basic serializer to expose all fields of XeroError.

    This is required by apps that import `XeroErrorSerializer`
    (e.g., `apps.workflow.views.xero.xero_view`).
    """

    class Meta:
        model = XeroError
        fields = "__all__"


class XeroErrorListResponseSerializer(serializers.Serializer):
    """Serializer for paginated Xero error list response."""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = XeroErrorSerializer(many=True)


class XeroErrorDetailResponseSerializer(serializers.Serializer):
    """Serializer for single Xero error detail response."""

    # Uses all the fields from XeroErrorSerializer
    id = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    entity = serializers.CharField()
    operation = serializers.CharField()
    error_type = serializers.CharField()
    error_message = serializers.CharField()
    xero_id = serializers.CharField(allow_null=True)
    context = serializers.JSONField()


class XeroAuthenticationErrorResponseSerializer(serializers.Serializer):
    """Serializer for Xero authentication error responses."""

    success = serializers.BooleanField(default=False)
    redirect_to_auth = serializers.BooleanField(default=True)
    message = serializers.CharField()


class XeroOperationResponseSerializer(serializers.Serializer):
    """Serializer for Xero operation responses (create/delete)."""

    success = serializers.BooleanField()
    error = serializers.CharField(required=False)
    messages = serializers.ListField(child=serializers.CharField(), required=False)


class XeroSyncInfoResponseSerializer(serializers.Serializer):
    """Serializer for Xero sync info response."""

    last_syncs = serializers.DictField()
    sync_range = serializers.CharField()
    sync_in_progress = serializers.BooleanField()
    error = serializers.CharField(required=False)
    redirect_to_auth = serializers.BooleanField(required=False)


class XeroSyncStartResponseSerializer(serializers.Serializer):
    """Serializer for start Xero sync response."""

    status = serializers.CharField()
    message = serializers.CharField()
    task_id = serializers.CharField(required=False)
    error = serializers.CharField(required=False)


class XeroTriggerSyncResponseSerializer(serializers.Serializer):
    """Serializer for trigger Xero sync response."""

    success = serializers.BooleanField()
    task_id = serializers.CharField(required=False)
    started = serializers.BooleanField(required=False)
    message = serializers.CharField(required=False)


class XeroPingResponseSerializer(serializers.Serializer):
    """Serializer for Xero ping response."""

    connected = serializers.BooleanField()


# ---------------------------------------------------------------------------
# App Error Serializers
# ---------------------------------------------------------------------------


class AppErrorSerializer(serializers.ModelSerializer):
    """Basic serializer for AppError instances."""

    class Meta:
        model = AppError
        fields = "__all__"


class AppErrorListResponseSerializer(serializers.Serializer):
    """Serializer for paginated AppError list response."""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AppErrorSerializer(many=True)


class AppErrorDetailResponseSerializer(serializers.Serializer):
    """Serializer for single AppError detail response."""

    id = serializers.UUIDField()
    timestamp = serializers.DateTimeField()
    message = serializers.CharField()
    data = serializers.JSONField()
    app = serializers.CharField(allow_null=True)
    file = serializers.CharField(allow_null=True)
    function = serializers.CharField(allow_null=True)
    severity = serializers.IntegerField()
    job_id = serializers.UUIDField(allow_null=True)
    user_id = serializers.UUIDField(allow_null=True)
    resolved = serializers.BooleanField()
    resolved_by = serializers.UUIDField(allow_null=True)
    resolved_timestamp = serializers.DateTimeField(allow_null=True)
