"""
Client REST URLs

REST URLs for Client module following RESTful patterns:
- Clearly defined endpoints
- Appropriate HTTP verbs
- Consistent structure with other REST modules
"""

from django.urls import path

from apps.client.views.client_rest_views import (
    ClientContactCreateRestView,
    ClientContactsRestView,
    ClientCreateRestView,
    ClientJobsRestView,
    ClientListAllRestView,
    ClientRetrieveRestView,
    ClientSearchRestView,
    ClientUpdateRestView,
    JobContactRestView,
)

app_name = "clients_rest"

urlpatterns = [
    # Client list all REST endpoint
    path(
        "all/",
        ClientListAllRestView.as_view(),
        name="client_list_all_rest",
    ),
    # Client creation REST endpoint
    path(
        "create/",
        ClientCreateRestView.as_view(),
        name="client_create_rest",
    ),
    # Client search REST endpoint
    path(
        "search/",
        ClientSearchRestView.as_view(),
        name="client_search_rest",
    ),
    # Client retrieve REST endpoint
    path(
        "<uuid:client_id>/",
        ClientRetrieveRestView.as_view(),
        name="client_retrieve_rest",
    ),
    # Client update REST endpoint
    path(
        "<uuid:client_id>/update/",
        ClientUpdateRestView.as_view(),
        name="client_update_rest",
    ),
    # Client contacts REST endpoint
    path(
        "<uuid:client_id>/contacts/",
        ClientContactsRestView.as_view(),
        name="client_contacts_rest",
    ),
    # Client jobs REST endpoint
    path(
        "<uuid:client_id>/jobs/",
        ClientJobsRestView.as_view(),
        name="client_jobs_rest",
    ),
    # Client contact creation REST endpoint
    path(
        "contacts/",
        ClientContactCreateRestView.as_view(),
        name="client_contact_create_rest",
    ),
    # Job contact REST endpoint
    path(
        "jobs/<uuid:job_id>/contact/",
        JobContactRestView.as_view(),
        name="job_contact_rest",
    ),
]
