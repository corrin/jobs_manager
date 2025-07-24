"""
Client REST Views

REST views for the Client module following clean code principles:
- SRP (Single Responsibility Principle)
- Early return and guard clauses
- Delegation to service layer
- Views as orchestrators only
"""

import json
import logging
from typing import Any, Dict

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from xero_python.accounting import AccountingApi

from apps.client.forms import ClientForm
from apps.client.models import Client, ClientContact
from apps.client.serializers import (
    ClientContactCreateRequestSerializer,
    ClientContactCreateResponseSerializer,
    ClientContactsResponseSerializer,
    ClientCreateRequestSerializer,
    ClientCreateResponseSerializer,
    ClientDuplicateErrorResponseSerializer,
    ClientErrorResponseSerializer,
    ClientListResponseSerializer,
    ClientNameOnlySerializer,
    ClientSearchResponseSerializer,
)
from apps.workflow.api.xero.sync import sync_clients
from apps.workflow.api.xero.xero import api_client, get_tenant_id, get_valid_token

logger = logging.getLogger(__name__)


class ClientListAllRestView(APIView):
    """
    REST view for listing all clients.
    Used by dropdowns and advanced search.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ClientListResponseSerializer

    def get(self, request: Request) -> Response:
        """
        Lists all clients (only id and name) for fast dropdowns.
        """
        try:
            clients = Client.objects.all().order_by("name")
            serializer = ClientNameOnlySerializer(clients, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error fetching all clients: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error fetching all clients", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClientSearchRestView(APIView):
    """
    REST view for client search.
    Implements name-based search functionality with pagination.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ClientSearchResponseSerializer

    def get(self, request: Request) -> Response:
        """
        Searches clients by name following early return pattern.
        """
        try:
            # Guard clause: validate query parameter
            query = request.GET.get("q", "").strip()
            if not query:
                response_data = {"results": []}
                serializer = ClientSearchResponseSerializer(data=response_data)
                serializer.is_valid(raise_exception=True)
                return Response(serializer.data)

            # Guard clause: query too short
            if len(query) < 3:
                response_data = {"results": []}
                serializer = ClientSearchResponseSerializer(data=response_data)
                serializer.is_valid(raise_exception=True)
                return Response(serializer.data)

            # Search clients following clean code principles
            clients = self._search_clients(query)
            results = self._format_client_results(clients)

            response_data = {"results": results}
            serializer = ClientSearchResponseSerializer(data=response_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error searching clients: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error searching clients", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _search_clients(self, query: str):
        """
        Executes client search with appropriate filters.
        SRP: single responsibility for searching clients.
        """
        return Client.objects.filter(Q(name__icontains=query)).order_by("name")[:10]

    def _format_client_results(self, clients) -> list:
        """
        Formats search results following SRP.
        """
        return [
            {
                "id": str(client.id),
                "name": client.name,
                "email": client.email or "",
                "phone": client.phone or "",
                "address": client.address or "",
                "is_account_customer": client.is_account_customer,
                "xero_contact_id": client.xero_contact_id or "",
                "last_invoice_date": (
                    client.get_last_invoice_date().strftime("%d/%m/%Y")
                    if client.get_last_invoice_date()
                    else ""
                ),
                "total_spend": f"${client.get_total_spend():,.2f}",
                "raw_json": client.raw_json,
            }
            for client in clients
        ]


class ClientContactsRestView(APIView):
    """
    REST view for fetching contacts of a client.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ClientContactsResponseSerializer

    def get(self, request: Request, client_id: str) -> Response:
        """
        Fetches contacts for a specific client.
        """
        try:
            # Guard clause: validate client_id
            if not client_id:
                error_serializer = ClientErrorResponseSerializer(
                    data={"error": "Client ID is required"}
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            # Fetch client with early return
            try:
                client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                error_serializer = ClientErrorResponseSerializer(
                    data={"error": "Client not found"}
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

            # Fetch client contacts
            contacts = self._get_client_contacts(client)
            results = self._format_contact_results(contacts)

            response_data = {"results": results}
            serializer = ClientContactsResponseSerializer(data=response_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching client contacts: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error fetching client contacts", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_client_contacts(self, client):
        """
        Fetches client contacts following SRP.
        """
        return client.contacts.all().order_by("name")

    def _format_contact_results(self, contacts) -> list:
        """
        Formats contact results following SRP.
        """
        return [
            {
                "id": str(contact.id),
                "name": contact.name,
                "email": contact.email or "",
                "phone": contact.phone or "",
                "position": contact.position or "",
                "is_primary": contact.is_primary,
            }
            for contact in contacts
        ]


class ClientContactCreateRestView(APIView):
    """
    REST view for creating client contacts.
    Follows SRP - single responsibility of orchestrating contact creation.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ClientContactCreateResponseSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method == "POST":
            return ClientContactCreateRequestSerializer
        return ClientContactCreateResponseSerializer

    def post(self, request: Request) -> Response:
        """
        Create a new client contact.

        Expected JSON:
        {
            "client_id": "uuid-of-client",
            "name": "Contact Name",
            "email": "contact@example.com",
            "phone": "123-456-7890",
            "position": "Job Title",
            "is_primary": false,
            "notes": "Additional notes"
        }
        """
        try:
            # Validate input data
            input_serializer = ClientContactCreateRequestSerializer(data=request.data)
            if not input_serializer.is_valid():
                error_serializer = ClientErrorResponseSerializer(
                    data={"error": f"Invalid input data: {input_serializer.errors}"}
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            validated_data = input_serializer.validated_data
            logger.info(f"Received contact creation data: {validated_data}")
            contact = self._create_contact(validated_data)

            response_data = {
                "success": True,
                "contact": {
                    "id": str(contact.id),
                    "name": contact.name,
                    "email": contact.email or "",
                    "phone": contact.phone or "",
                    "position": contact.position or "",
                    "is_primary": contact.is_primary,
                    "notes": contact.notes or "",
                },
                "message": "Contact created successfully",
            }

            response_serializer = ClientContactCreateResponseSerializer(
                data=response_data
            )
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating contact: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error creating contact", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_json_body(self, request: Request) -> Dict[str, Any]:
        """
        Parse JSON body with early return pattern.
        """
        if not request.body:
            raise ValueError("Request body is empty")

        try:
            return json.loads(request.body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")

    def _create_contact(self, data: Dict[str, Any]) -> ClientContact:
        """
        Create contact following validation and business rules.
        Apply guard clauses for required fields.
        """
        # Guard clauses - validate required fields
        if "client_id" not in data:
            raise ValueError("client_id is required")

        if "name" not in data or not data["name"].strip():
            raise ValueError("name is required")

        # Get client with early return on not found
        try:
            client = Client.objects.get(id=data["client_id"])
        except Client.DoesNotExist:
            raise ValueError("Client not found")

        # Create contact following clean data handling
        contact = ClientContact.objects.create(
            client=client,
            name=data["name"].strip(),
            email=data.get("email", "").strip() or None,
            phone=data.get("phone", "").strip() or None,
            position=data.get("position", "").strip() or None,
            is_primary=data.get("is_primary", False),
            notes=data.get("notes", "").strip() or None,
        )

        return contact


class ClientCreateRestView(APIView):
    """
    REST view for creating new clients.
    Follows clean code principles and delegates to Django forms for validation.
    Now creates client in Xero first, then syncs locally.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ClientCreateResponseSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method == "POST":
            return ClientCreateRequestSerializer
        return ClientCreateResponseSerializer

    def post(self, request: Request) -> Response:
        """
        Create a new client, first in Xero, then sync locally.
        """
        try:
            # Validate input data
            input_serializer = ClientCreateRequestSerializer(data=request.data)
            if not input_serializer.is_valid():
                error_serializer = ClientErrorResponseSerializer(
                    data={"error": f"Invalid input data: {input_serializer.errors}"}
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            validated_data = input_serializer.validated_data
            form = ClientForm(validated_data)
            if not form.is_valid():
                error_messages = []
                for field, errors in form.errors.items():
                    error_messages.extend([f"{field}: {error}" for error in errors])
                error_serializer = ClientErrorResponseSerializer(
                    data={"error": "; ".join(error_messages)}
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            # Xero token check
            token = get_valid_token()
            if not token:
                error_serializer = ClientErrorResponseSerializer(
                    data={"error": "Xero authentication required"}
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_401_UNAUTHORIZED
                )

            accounting_api = AccountingApi(api_client)
            xero_tenant_id = get_tenant_id()
            name = form.cleaned_data["name"]

            # Check for duplicates in Xero
            existing_contacts = accounting_api.get_contacts(
                xero_tenant_id, where=f'Name="{name}"'
            )
            if existing_contacts and existing_contacts.contacts:
                xero_client = existing_contacts.contacts[0]
                xero_contact_id = getattr(xero_client, "contact_id", "")
                duplicate_error_data = {
                    "error": f"Client '{name}' already exists in Xero",
                    "existing_client": {
                        "name": name,
                        "xero_contact_id": xero_contact_id,
                    },
                }
                error_serializer = ClientDuplicateErrorResponseSerializer(
                    data=duplicate_error_data
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(error_serializer.data, status=status.HTTP_409_CONFLICT)

            # Create new contact in Xero
            contact_data = {
                "name": name,
                "emailAddress": form.cleaned_data["email"] or "",
                "phones": [
                    {
                        "phoneType": "DEFAULT",
                        "phoneNumber": form.cleaned_data["phone"] or "",
                    }
                ],
                "addresses": [
                    {
                        "addressType": "STREET",
                        "addressLine1": form.cleaned_data["address"] or "",
                    }
                ],
                "isCustomer": form.cleaned_data["is_account_customer"],
            }
            response = accounting_api.create_contacts(
                xero_tenant_id, contacts={"contacts": [contact_data]}
            )
            if (
                not response
                or not hasattr(response, "contacts")
                or not response.contacts
            ):
                raise ValueError("No contact data in Xero response")
            if len(response.contacts) != 1:
                raise ValueError(
                    f"Expected 1 contact in response, got {len(response.contacts)}"
                )

            # Sync locally
            client_instances = sync_clients(response.contacts)
            if not client_instances:
                raise ValueError("Failed to sync client from Xero")
            created_client = client_instances[0]

            response_data = {
                "success": True,
                "client": self._format_client_data(created_client),
                "message": f'Client "{created_client.name}" created successfully',
            }

            response_serializer = ClientCreateResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating client (Xero sync): {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error creating client (Xero sync)", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _parse_json_data(self, request: Request) -> Dict[str, Any]:
        """
        Parse JSON data from request following SRP.
        """
        try:
            return json.loads(request.body)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON data")

    def _create_client(self, data: Dict[str, Any]) -> Client:
        """
        Create client using Django form validation.
        """
        # Use ClientForm for validation following Django best practices
        form = ClientForm(data)

        # Guard clause - validate form
        if not form.is_valid():
            error_messages = []
            for field, errors in form.errors.items():
                error_messages.extend([f"{field}: {error}" for error in errors])
            raise ValueError("; ".join(error_messages))

        # Create client with transaction for data integrity
        with transaction.atomic():
            client = form.save(commit=False)

            # Set required fields that aren't in the form
            client.xero_last_modified = timezone.now()
            client.xero_last_synced = timezone.now()

            client.save()
            logger.info(f"Created client: {client.name} (ID: {client.id})")

        return client

    def _format_client_data(self, client: Client) -> Dict[str, Any]:
        """
        Format client data for response following SRP.
        """
        return {
            "id": str(client.id),
            "name": client.name,
            "email": client.email or "",
            "phone": client.phone or "",
            "address": client.address or "",
            "is_account_customer": client.is_account_customer,
            "xero_contact_id": client.xero_contact_id or "",
            "last_invoice_date": client.get_last_invoice_date() or "",
            "total_spend": client.get_total_spend() or "0.00",
        }
