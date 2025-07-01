"""
URL Configuration for Workflow App

URL Structure Patterns:
----------------------

1. Resource-based URL paths:
   - Primary resources have their own root path: /{resource}/
   - Examples: /xero/, /clients/, /invoices/, /job/, /kanban/

2. API Endpoints:
   - All API endpoints are prefixed with /api/
   - Follow pattern: /api/{resource}/{action}/
   - Examples: /api/xero/authenticate/, /api/clients/all/

3. Resource Actions:
   - List view: /{resource}/
   - Detail view: /{resource}/{id}/
   - Create: /{resource}/add/ or /api/{resource}/create/
   - Update: /{resource}/{id}/update/
   - Delete: /api/{resource}/{id}/delete/

4. Nested Resources:
   - Follow pattern: /{parent-resource}/{id}/{child-resource}/
   - Example: /job/{id}/workshop-pdf/

5. URL Names:
   - Use resource_action format
   - Examples: client_detail, job_create, invoice_update

6. Ordering:
   - URLs MUST be kept in strict alphabetical order by path
   - Group URLs logically (api/, resource roots) but maintain alphabetical order within each group
   - Comments may be used to denote logical groupings but do not break alphabetical ordering

Follow these patterns when adding new URLs to maintain consistency.
"""

import debug_toolbar
from django.urls import include, path
from django.views.generic import RedirectView

from apps.workflow.api.enums import get_enum_choices
from apps.workflow.views.company_defaults_api import CompanyDefaultsAPIView
from apps.workflow.views.xero import xero_view
from apps.workflow.xero_webhooks import XeroWebhookView

urlpatterns = [
    # Redirect to Kanban board
    path("", RedirectView.as_view(url="/kanban/"), name="home"),
    path("api/enums/<str:enum_name>/", get_enum_choices, name="get_enum_choices"),
    path(
        "api/xero/authenticate/",
        xero_view.xero_authenticate,
        name="api_xero_authenticate",
    ),
    path(
        "api/xero/oauth/callback/",
        xero_view.xero_oauth_callback,
        name="xero_oauth_callback",
    ),
    path(
        "api/xero/disconnect/",
        xero_view.xero_disconnect,
        name="xero_disconnect",
    ),
    path(
        "api/xero/sync-stream/",
        xero_view.stream_xero_sync,
        name="stream_xero_sync",
    ),
    path(
        "api/xero/create_invoice/<uuid:job_id>",
        xero_view.create_xero_invoice,
        name="create_invoice",
    ),
    path(
        "api/xero/delete_invoice/<uuid:job_id>",
        xero_view.delete_xero_invoice,
        name="delete_invoice",
    ),
    path(
        "api/xero/create_quote/<uuid:job_id>",
        xero_view.create_xero_quote,
        name="create_quote",
    ),
    path(
        "api/xero/delete_quote/<uuid:job_id>",
        xero_view.delete_xero_quote,
        name="delete_quote",
    ),
    path(
        "api/xero/sync-info/",
        xero_view.get_xero_sync_info,
        name="xero_sync_info",
    ),
    path(
        "api/xero/create_purchase_order/<uuid:purchase_order_id>",
        xero_view.create_xero_purchase_order,
        name="create_xero_purchase_order",
    ),
    path(
        "api/xero/delete_purchase_order/<uuid:purchase_order_id>",
        xero_view.delete_xero_purchase_order,
        name="delete_xero_purchase_order",
    ),
    path(
        "api/xero/sync/",
        xero_view.start_xero_sync,
        name="synchronise_xero_data",
    ),
    path(
        "api/xero/webhook/",
        XeroWebhookView.as_view(),
        name="xero_webhook",
    ),
    path(
        "api/xero/ping/",
        xero_view.xero_ping,
        name="xero_ping",
    ),
    path(
        "xero-errors/",
        xero_view.XeroErrorListAPIView.as_view(),
        name="xero-error-list",
    ),
    path(
        "xero-errors/<uuid:pk>/",
        xero_view.XeroErrorDetailAPIView.as_view(),
        name="xero-error-detail",
    ),
    path("xero/", xero_view.XeroIndexView.as_view(), name="xero_index"),
    path(
        "xero/sync-progress/",
        xero_view.xero_sync_progress_page,
        name="xero_sync_progress",
    ),
    path(
        "api/company-defaults/",
        CompanyDefaultsAPIView.as_view(),
        name="api_company_defaults",
    ),
    path("__debug__/", include(debug_toolbar.urls)),
    # End of URL patterns
]
