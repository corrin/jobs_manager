"""
URL Configuration for Client App

This module contains all URL patterns related to client management:
- Client CRUD operations
- Client contacts
- Client search
- REST API endpoints under /rest/
"""

from django.urls import include, path

app_name = "client"

urlpatterns = [
    # REST API endpoints
    path("rest/", include("apps.client.urls_rest")),
]
