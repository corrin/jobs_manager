from rest_framework import serializers

from apps.client.models import Client, ClientContact


class ClientContactSerializer(serializers.ModelSerializer):
    """Serializer for ClientContact model."""

    class Meta:
        model = ClientContact
        fields = [
            "id",
            "client",
            "name",
            "email",
            "phone",
            "position",
            "is_primary",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClientSerializer(serializers.ModelSerializer):
    contacts = ClientContactSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = "__all__"


class ClientNameOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]


class ClientContactListResponseSerializer(serializers.Serializer):
    """Serialiser for client contact list response"""

    id = serializers.IntegerField()
    client = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    position = serializers.CharField(allow_blank=True)
    is_primary = serializers.BooleanField()
    notes = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class StandardErrorSerializer(serializers.Serializer):
    """Standard serialiser for error responses"""

    error = serializers.CharField()
    details = serializers.JSONField(required=False)


class ClientListResponseSerializer(serializers.Serializer):
    """Serializer for client list response"""

    id = serializers.CharField()
    name = serializers.CharField()


class ClientSearchResultSerializer(serializers.Serializer):
    """Serializer for individual client search result"""

    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    is_account_customer = serializers.BooleanField()
    xero_contact_id = serializers.CharField(allow_blank=True)
    last_invoice_date = serializers.CharField(allow_blank=True)
    total_spend = serializers.CharField()
    raw_json = serializers.JSONField(required=False)


class ClientSearchResponseSerializer(serializers.Serializer):
    """Serializer for client search response"""

    results = ClientSearchResultSerializer(many=True)


class ClientContactResultSerializer(serializers.Serializer):
    """Serializer for individual client contact result"""

    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    position = serializers.CharField(allow_blank=True)
    is_primary = serializers.BooleanField()


class ClientContactsResponseSerializer(serializers.Serializer):
    """Serializer for client contacts response"""

    results = ClientContactResultSerializer(many=True)


class ClientContactCreateRequestSerializer(serializers.Serializer):
    """Serializer for client contact creation request"""

    client_id = serializers.UUIDField()
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    position = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_primary = serializers.BooleanField(default=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class ClientContactCreateResponseSerializer(serializers.Serializer):
    """Serializer for client contact creation response"""

    success = serializers.BooleanField()
    contact = ClientContactResultSerializer()
    message = serializers.CharField()


class ClientCreateRequestSerializer(serializers.Serializer):
    """Serializer for client creation request"""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    is_account_customer = serializers.BooleanField(default=True)


class ClientCreateResponseSerializer(serializers.Serializer):
    """Serializer for client creation response"""

    success = serializers.BooleanField()
    client = ClientSearchResultSerializer()
    message = serializers.CharField()


class ClientErrorResponseSerializer(serializers.Serializer):
    """Serializer for client error responses"""

    success = serializers.BooleanField(default=False)
    error = serializers.CharField()
    details = serializers.CharField(required=False)


class ClientDuplicateErrorResponseSerializer(serializers.Serializer):
    """Serializer for client duplicate error response"""

    success = serializers.BooleanField(default=False)
    error = serializers.CharField()
    existing_client = serializers.DictField()
