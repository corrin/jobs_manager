import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Staff

logger = logging.getLogger(__name__)


class EmptySerializer(serializers.Serializer):
    """An empty serializer for schema generation. Helper serializer for CustomTokenObtainPairView."""


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer that accepts username and maps it to email
    """

    username_field = "username"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Add username field instead of email
        if "username" not in self.fields:
            self.fields["username"] = serializers.CharField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
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


class GenericStaffMethodsMixin:
    """
    Utilitary methods shared between StaffSerializer and StaffCreateSerializer
    - Normalises arrays received as "" (groups, user_permissions)
    - Normalises decimal fields received as "" to "0.00" (wage_rate, hours_*)
    """

    ARRAY_FIELDS = ["groups", "user_permissions"]
    DECIMAL_FIELDS = [
        "wage_rate",
        "hours_mon",
        "hours_tue",
        "hours_wed",
        "hours_thu",
        "hours_fri",
        "hours_sat",
        "hours_sun",
    ]

    def to_internal_value(self, data: Any) -> Dict[str, Any]:
        is_querydict = hasattr(data, "getlist")
        if is_querydict:
            data = data.copy()

        for field in self.ARRAY_FIELDS:
            if is_querydict:
                values = data.getlist(field)
                if values == [""] or values == [] or not values:
                    data.setlist(field, [])
            else:
                value = data.get(field)
                if value in ("", None):
                    data[field] = []

        for field in self.DECIMAL_FIELDS:
            if is_querydict:
                value = data.get(field)
                if value == "":
                    data[field] = "0.00"
            else:
                if field in data and data[field] == "":
                    data[field] = str(Decimal("0.00"))

        return super().to_internal_value(data)


class BaseStaffSerializer(GenericStaffMethodsMixin, serializers.ModelSerializer):
    """Base serializer for Staff model with shared logic for create and update operations."""


class StaffSerializer(BaseStaffSerializer):
    icon = serializers.ImageField(required=False, allow_null=True)

    def update(self, instance: Staff, validated_data: Dict[str, Any]) -> Staff:
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)

    class Meta:
        model = Staff
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "password",
            "wage_rate",
            "ims_payroll_id",
            "icon",
            "raw_ims_data",
            "xero_user_id",
            "date_left",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
            "hours_mon",
            "hours_tue",
            "hours_wed",
            "hours_thu",
            "hours_fri",
            "hours_sat",
            "hours_sun",
            # Read-only fields
            "last_login",
            "date_joined",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_login",
            "date_joined",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "password": {"required": False, "write_only": True},
            "groups": {"required": False},
            "user_permissions": {"required": False},
            "preferred_name": {"required": False},
            "ims_payroll_id": {"required": False},
            "raw_ims_data": {"required": False},
            "xero_user_id": {"required": False},
            "date_left": {"required": False},
            "icon": {"required": False},
        }


class StaffCreateSerializer(BaseStaffSerializer):
    icon = serializers.ImageField(required=False, allow_null=True)

    def create(self, validated_data: Dict[str, Any]) -> Staff:
        password = validated_data.pop("password", None)

        instance = super().create(validated_data)

        if password:
            instance.set_password(password)
        else:
            instance.set_unusable_password()

        instance.save()

        return instance

    def to_representation(self, instance):
        return StaffSerializer(instance, context=self.context).data

    class Meta:
        model = Staff
        fields = [
            "first_name",
            "last_name",
            "preferred_name",
            "email",
            "password",
            "wage_rate",
            "ims_payroll_id",
            "icon",
            "hours_mon",
            "hours_tue",
            "hours_wed",
            "hours_thu",
            "hours_fri",
            "hours_sat",
            "hours_sun",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        ]

        extra_kwargs = {
            "password": {"required": True, "write_only": True},
            "groups": {"required": False},
            "user_permissions": {"required": False},
            "preferred_name": {"required": False},
        }


class KanbanStaffSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    def get_icon(self, obj: Staff) -> Optional[str]:
        if obj.icon:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.icon.url) if request else obj.icon.url
        return None

    def get_display_name(self, obj: Staff) -> str:
        return obj.get_display_full_name()

    class Meta:
        model = Staff
        fields = ["id", "first_name", "last_name", "icon", "display_name"]
        read_only_fields = ["display_name"]


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile information returned by /accounts/me/"""

    username = serializers.CharField(source="email", read_only=True)
    fullName = serializers.SerializerMethodField()
    preferred_name = serializers.CharField(
        read_only=True,
        required=False,
        allow_null=True,  # <-- To DRF-Spectacular that null is allowed
        help_text="Preferred name (may be null)",
    )
    is_active = serializers.SerializerMethodField()

    def get_fullName(self, obj: Staff) -> str:
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_is_active(self, obj: Staff) -> bool:
        logger.warning(
            "get_is_active method in UserProfileSerializer is deprecated. You must pass a date"
        )
        return obj.is_currently_active

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


class TokenObtainPairResponseSerializer(serializers.Serializer):
    """
    Serializer for the response of the token obtain pair view.
    This is used to properly document the API response schema.

    All fields are optional because when ENABLE_JWT_AUTH=True,
    tokens are set as httpOnly cookies and removed from the JSON response.
    """

    access = serializers.CharField(
        required=False,
        help_text="JWT access token (only present when not using httpOnly cookies)",
    )
    refresh = serializers.CharField(
        required=False,
        help_text="JWT refresh token (only present when not using httpOnly cookies)",
    )
    password_needs_reset = serializers.BooleanField(
        required=False,
        help_text="Indicates if the user needs to reset their password",
    )
    password_reset_url = serializers.URLField(
        required=False, help_text="URL to reset password if needed"
    )


class TokenRefreshResponseSerializer(serializers.Serializer):
    """
    Serializer for the response of the token refresh view.
    This is used to properly document the API response schema.

    The access field is optional because when ENABLE_JWT_AUTH=True,
    the token is set as an httpOnly cookie and removed from the JSON response.
    """

    access = serializers.CharField(
        required=False,
        help_text="New JWT access token (only present when not using httpOnly cookies)",
    )
