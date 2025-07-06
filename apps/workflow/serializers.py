from rest_framework import serializers

# Existing models used in this serializer module
from .models import XeroError  # Added to support XeroErrorSerializer
from .models import AIProvider, CompanyDefaults, XeroAccount, XeroToken


class XeroTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = XeroToken
        fields = "__all__"


class CompanyDefaultsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyDefaults
        fields = "__all__"


class XeroAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = XeroAccount
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
