from rest_framework import serializers

from apps.job.models import JobQuoteChat


class JobQuoteChatSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new JobQuoteChat messages.
    Validates required fields and business rules.
    """

    class Meta:
        model = JobQuoteChat
        fields = ["message_id", "role", "content", "metadata"]
        extra_kwargs = {"metadata": {"default": dict, "required": False}}

    def validate_role(self, value):
        """Validate that role is either 'user' or 'assistant'."""
        if value not in ["user", "assistant"]:
            raise serializers.ValidationError("role must be 'user' or 'assistant'")
        return value

    def validate_message_id(self, value):
        """Validate that message_id is unique."""
        if JobQuoteChat.objects.filter(message_id=value).exists():
            raise serializers.ValidationError("message_id already exists")
        return value


class JobQuoteChatUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing JobQuoteChat messages.
    Used for PATCH operations, especially streaming response updates.
    """

    class Meta:
        model = JobQuoteChat
        fields = ["content", "metadata"]
        extra_kwargs = {"content": {"required": False}, "metadata": {"required": False}}

    def update(self, instance, validated_data):
        """Update instance with proper metadata merging."""
        # Update content if provided
        if "content" in validated_data:
            instance.content = validated_data["content"]

        # Merge metadata instead of replacing
        if "metadata" in validated_data:
            current_metadata = instance.metadata or {}
            current_metadata.update(validated_data["metadata"])
            instance.metadata = current_metadata

        instance.save()
        return instance
