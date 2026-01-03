"""
API endpoint for CompanyDefaults schema/metadata.

Provides field metadata so frontend can dynamically render settings UI.
"""

from typing import Any

from django.db import models
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workflow.models import CompanyDefaults
from apps.workflow.models.settings_metadata import (
    COMPANY_DEFAULTS_FIELD_SECTIONS,
    COMPANY_DEFAULTS_READ_ONLY_FIELDS,
    SettingsSection,
    get_field_metadata,
)
from apps.workflow.serializers import CompanyDefaultsSchemaSerializer


class CompanyDefaultsSchemaAPIView(APIView):
    """
    API endpoint that returns field metadata for CompanyDefaults.

    This enables the frontend to dynamically render settings UI
    without hardcoding field definitions.

    GET /api/company-defaults/schema/

    Returns sections with their fields, ordered for UI display.
    Fields marked as 'internal' section are excluded from the response.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: CompanyDefaultsSchemaSerializer},
        examples=[
            OpenApiExample(
                "Example Response",
                value={
                    "sections": [
                        {
                            "key": "general",
                            "title": "General Settings",
                            "order": 1,
                            "fields": [
                                {
                                    "key": "company_name",
                                    "label": "Company Name",
                                    "type": "text",
                                    "required": True,
                                    "help_text": "",
                                    "section": "general",
                                }
                            ],
                        }
                    ]
                },
            )
        ],
    )
    def get(self, request: Request) -> Response:
        """Return schema metadata for CompanyDefaults fields."""
        sections_dict: dict[str, dict[str, Any]] = {}

        # Get all model fields
        model = CompanyDefaults
        for field in model._meta.get_fields():
            # Skip reverse relations and non-concrete fields
            if not isinstance(field, models.Field):
                continue

            field_name = field.name

            # Get section for this field
            section_key = COMPANY_DEFAULTS_FIELD_SECTIONS.get(field_name)
            if not section_key:
                continue  # Skip unmapped fields (fail-safe handled by system check)

            # Skip internal fields
            if section_key == "internal":
                continue

            # Get or create section entry
            if section_key not in sections_dict:
                section_info = SettingsSection.get_section_info(section_key)
                if section_info:
                    sections_dict[section_key] = {
                        "key": section_key,
                        "title": section_info[1],
                        "order": section_info[2],
                        "fields": [],
                    }

            # Add field metadata
            if section_key in sections_dict:
                field_meta = get_field_metadata(
                    field, field_name, COMPANY_DEFAULTS_READ_ONLY_FIELDS
                )
                sections_dict[section_key]["fields"].append(field_meta)

        # Convert to sorted list
        sections = sorted(sections_dict.values(), key=lambda s: s["order"])

        return Response({"sections": sections})
