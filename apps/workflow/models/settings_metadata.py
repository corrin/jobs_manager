"""
Settings field metadata for dynamic UI generation.

This module provides:
1. SettingsSection - enum-like class defining valid sections
2. Field metadata extraction utilities
3. Django-to-UI field type mapping

When adding a new field to CompanyDefaults:
1. Add the field to the model with help_text
2. Add the field name to COMPANY_DEFAULTS_FIELD_SECTIONS below
3. The system check will catch any missing mappings at startup
"""

from typing import Any

from django.db import models


class SettingsSection:
    """
    Registry of valid settings sections with display metadata.

    Each section is a tuple of (key, title, order).
    Order determines display sequence in the UI.
    """

    GENERAL = ("general", "General", 1)
    GOOGLE = ("google", "Google", 2)
    XERO = ("xero", "Xero", 3)
    KPI = ("kpi", "KPI", 4)
    AI = ("ai", "AI", 5)
    WORKING_HOURS = ("working_hours", "Working Hours", 6)
    ADDRESS = ("address", "Address", 7)
    CONTACT = ("contact", "Contact", 8)
    INTERNAL = ("internal", "Internal", 99)  # Hidden from UI

    @classmethod
    def all_sections(cls) -> list[tuple[str, str, int]]:
        """Return all sections as list of (key, title, order) tuples."""
        return [
            v
            for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, tuple) and len(v) == 3
        ]

    @classmethod
    def get_section_info(cls, key: str) -> tuple[str, str, int] | None:
        """Get section info by key."""
        for section in cls.all_sections():
            if section[0] == key:
                return section
        return None


# Mapping from Django field types to UI input types
DJANGO_TO_UI_TYPE: dict[type["models.Field[Any, Any]"], str] = {
    models.CharField: "text",
    models.TextField: "text",
    models.IntegerField: "number",
    models.DecimalField: "number",
    models.FloatField: "number",
    models.BooleanField: "boolean",
    models.EmailField: "text",
    models.URLField: "text",
    models.TimeField: "text",
    models.DateField: "date",
    models.DateTimeField: "text",
}


# Fields that should not be editable via the API (e.g., primary keys)
COMPANY_DEFAULTS_READ_ONLY_FIELDS: set[str] = {
    "company_name",
    "last_xero_sync",
    "last_xero_deep_sync",
}

# Field name to section mapping for CompanyDefaults
# This is the authoritative source for which section each field belongs to.
# Adding a field to CompanyDefaults without adding it here will cause a startup error.
COMPANY_DEFAULTS_FIELD_SECTIONS: dict[str, str] = {
    # General
    "company_name": "general",
    "company_acronym": "general",
    "is_primary": "internal",
    "time_markup": "general",
    "materials_markup": "general",
    "charge_out_rate": "general",
    "wage_rate": "general",
    "starting_job_number": "general",
    "starting_po_number": "general",
    "po_prefix": "general",
    "shop_client_name": "general",
    "test_client_name": "general",
    # Google
    "master_quote_template_url": "google",
    "master_quote_template_id": "google",
    "gdrive_quotes_folder_url": "google",
    "gdrive_quotes_folder_id": "google",
    # Xero integration
    "xero_tenant_id": "xero",
    "xero_payroll_calendar_name": "xero",
    "last_xero_sync": "xero",
    "last_xero_deep_sync": "xero",
    "xero_shortcode": "internal",
    "xero_payroll_calendar_id": "internal",
    # KPI thresholds
    "billable_threshold_green": "kpi",
    "billable_threshold_amber": "kpi",
    "daily_gp_target": "kpi",
    "shop_hours_target_percentage": "kpi",
    # Working hours
    "mon_start": "working_hours",
    "mon_end": "working_hours",
    "tue_start": "working_hours",
    "tue_end": "working_hours",
    "wed_start": "working_hours",
    "wed_end": "working_hours",
    "thu_start": "working_hours",
    "thu_end": "working_hours",
    "fri_start": "working_hours",
    "fri_end": "working_hours",
    # Address
    "address_line1": "address",
    "address_line2": "address",
    "suburb": "address",
    "city": "address",
    "post_code": "address",
    "country": "address",
    # Contact
    "company_email": "contact",
    "company_url": "contact",
    # Internal - auto-managed fields, not shown in UI
    "created_at": "internal",
    "updated_at": "internal",
}


def get_ui_type_for_field(field: "models.Field[Any, Any]") -> str:
    """
    Determine the UI input type for a Django model field.

    Returns a string like 'text', 'number', 'boolean', etc.
    """
    for field_class, ui_type in DJANGO_TO_UI_TYPE.items():
        if isinstance(field, field_class):
            return ui_type
    return "text"  # Default fallback


def get_field_metadata(
    field: "models.Field[Any, Any]",
    field_name: str,
    read_only_fields: set[str] | None = None,
) -> dict[str, Any]:
    """
    Extract metadata from a Django model field for UI rendering.

    Returns dict with: key, label, type, required, help_text, section, read_only
    """
    section = COMPANY_DEFAULTS_FIELD_SECTIONS.get(field_name, "company")

    # Get label from verbose_name or derive from field name
    if field.verbose_name and field.verbose_name != field_name.replace("_", " "):
        label = str(field.verbose_name).title()
    else:
        label = field_name.replace("_", " ").title()

    return {
        "key": field_name,
        "label": label,
        "type": get_ui_type_for_field(field),
        "required": not field.blank and not field.null,
        "help_text": field.help_text or "",
        "section": section,
        "read_only": field_name in (read_only_fields or set()),
    }
