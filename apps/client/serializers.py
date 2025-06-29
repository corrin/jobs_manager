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
