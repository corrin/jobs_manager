"""Constants used by the Xero API integration."""

XERO_SCOPES = [
    "offline_access",
    "openid",
    "profile",
    "email",
    "accounting.contacts",
    "accounting.transactions",
    "accounting.reports.read",
    "accounting.settings",
    "accounting.journals.read",
    # "accounting.inventory",  # REMOVED - invalid scope, use accounting.settings instead
    "projects",
    "payroll.timesheets",
    "payroll.employees",
    "payroll.settings",
]
