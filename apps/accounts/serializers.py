from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Staff


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer that accepts username and maps it to email
    """

    username_field = "username"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add username field instead of email
        if "username" not in self.fields:
            self.fields["username"] = serializers.CharField()

    def validate(self, attrs):
        # Get username and password from request
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            # Since our User model uses email as USERNAME_FIELD,
            # we assume username is actually an email
            user = authenticate(
                request=self.context.get("request"),
                username=username,
                password=password,
            )

            if user and user.is_active:
                # Prepare data for parent class
                attrs[self.username_field] = username

                # Call parent validate method
                data = super().validate(attrs)
                return data

        # If we get here, authentication failed
        raise serializers.ValidationError("Invalid credentials")


class StaffSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        data = data.copy()  # QueryDict can be immutable, so we copy it
        for field in ["groups", "user_permissions"]:
            # Usually it comes as a QueryDict so we can use getlist directly without hasattr
            value = data.getlist(field)
            if value == [""]:
                data.setlist(field, [])
        return super().to_internal_value(data)

    def validate(self, attrs):
        return super().validate(attrs)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)

    class Meta:
        model = Staff
        fields = "__all__"
        extra_kwargs = {
            "password": {"required": False},
        }


class KanbanStaffSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    def get_icon(self, obj):
        if obj.icon:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.icon.url) if request else obj.icon.url
        return None

    def get_display_name(self, obj):
        return obj.get_display_full_name()

    class Meta:
        model = Staff
        fields = ["id", "first_name", "last_name", "icon", "display_name"]
        read_only_fields = ["display_name"]


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile information returned by /accounts/me/"""

    username = serializers.CharField(source="email", read_only=True)
    fullName = serializers.SerializerMethodField()
    preferred_name = serializers.CharField(read_only=True)

    def get_fullName(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    class Meta:
        model = Staff
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "fullName",
            "is_active",
            "is_staff",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "fullName",
            "is_active",
            "is_staff",
        ]
