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
    last_invoice_date = serializers.CharField(allow_null=True)
    total_spend = serializers.CharField()


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


class ClientContactResponseSerializer(serializers.Serializer):
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
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(
        max_length=50, required=False, allow_blank=True, allow_null=True
    )
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
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


class ClientDetailResponseSerializer(serializers.Serializer):
    """Serializer for client detail response"""

    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    is_account_customer = serializers.BooleanField()
    is_supplier = serializers.BooleanField()
    xero_contact_id = serializers.CharField(allow_blank=True)
    xero_tenant_id = serializers.CharField(allow_blank=True)
    primary_contact_name = serializers.CharField(allow_blank=True)
    primary_contact_email = serializers.CharField(allow_blank=True)
    additional_contact_persons = serializers.ListField(required=False)
    all_phones = serializers.ListField(required=False)
    xero_last_modified = serializers.CharField(allow_null=True)
    xero_last_synced = serializers.CharField(allow_null=True)
    xero_archived = serializers.BooleanField()
    xero_merged_into_id = serializers.CharField(allow_blank=True)
    merged_into = serializers.CharField(allow_null=True)
    django_created_at = serializers.CharField()
    django_updated_at = serializers.CharField()
    last_invoice_date = serializers.CharField(allow_null=True)
    total_spend = serializers.CharField()


class ClientUpdateRequestSerializer(serializers.Serializer):
    """Serializer for client update request"""

    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    is_account_customer = serializers.BooleanField(required=False)


class ClientUpdateResponseSerializer(serializers.Serializer):
    """Serializer for client update response"""

    success = serializers.BooleanField()
    client = ClientDetailResponseSerializer()
    message = serializers.CharField()


class JobContactResponseSerializer(serializers.Serializer):
    """Serializer for job contact information response"""

    id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.CharField(allow_blank=True, allow_null=True)
    phone = serializers.CharField(allow_blank=True, allow_null=True)
    position = serializers.CharField(allow_blank=True, allow_null=True)
    is_primary = serializers.BooleanField()
    notes = serializers.CharField(allow_blank=True, allow_null=True)


class JobContactUpdateRequestSerializer(JobContactResponseSerializer):
    """Serializer for job contact update request"""


class ClientJobHeaderSerializer(serializers.Serializer):
    """Serializer for job header in client jobs list"""

    job_id = serializers.UUIDField()
    job_number = serializers.IntegerField()
    name = serializers.CharField()
    client = serializers.DictField(allow_null=True)
    status = serializers.CharField()
    pricing_methodology = serializers.CharField(allow_null=True)
    fully_invoiced = serializers.BooleanField()
    has_quote_in_xero = serializers.BooleanField()
    is_fixed_price = serializers.BooleanField()
    quote_acceptance_date = serializers.CharField(allow_null=True)
    paid = serializers.BooleanField()
    rejected_flag = serializers.BooleanField()


class ClientJobsResponseSerializer(serializers.Serializer):
    """Serializer for client jobs list response"""

    results = ClientJobHeaderSerializer(many=True)
