"""
URL Configuration for Client App

This module contains all URL patterns related to client management:
- Client CRUD operations
- Client contact information
- Client search and listing
- Unused clients management
- etc.
"""

from django.urls import include, path

from apps.client.views import client_views

app_name = "clients"

urlpatterns = [
    # REST API endpoints
    path("rest/", include("apps.client.urls_rest")),
    # ClientContact API endpoints
    path(
        "api/client/<uuid:client_id>/contacts/",
        client_views.get_client_contacts_api,
        name="api_get_client_contacts",
    ),
    path(
        "api/client/contact/",
        client_views.create_client_contact_api,
        name="api_create_client_contact",
    ),
    path(
        "api/client/contact/<uuid:contact_id>/",
        client_views.client_contact_detail_api,
        name="api_client_contact_detail",
    ),
    # Client view endpoints
    path("", client_views.ClientListView.as_view(), name="list_clients"),
    path(
        "<uuid:pk>/",
        client_views.ClientUpdateView.as_view(),
        name="update_client",
    ),
    path("add/", client_views.AddClient, name="add_client"),
]
