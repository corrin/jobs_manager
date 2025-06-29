"""
Client REST Views

REST views for Client module following clean code principles:
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
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.client.forms import ClientForm
from apps.client.models import Client, ClientContact

logger = logging.getLogger(__name__)


class BaseClientRestView(View):
    """
    Base view for Client REST operations.
    Implements common functionality like JSON parsing and error handling.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def handle_error(
        self, error: Exception, message: str = "Internal server error"
    ) -> JsonResponse:
        """
        Centralise error handling following clean code principles.
        """
        logger.error(f"{message}: {str(error)}")
        return JsonResponse({"error": message, "details": str(error)}, status=500)


class ClientListAllRestView(BaseClientRestView):
    """
    REST view for listing all clients.
    Used by dropdowns and advanced search.
    """

    def get(self, request) -> JsonResponse:
        """
        Lista todos os clientes seguindo early return pattern.
        """
        try:
            # Busca todos os clientes ordenados por nome
            clients = self._get_all_clients()
            results = self._format_client_results(clients)

            return JsonResponse(results, safe=False)

        except Exception as e:
            return self.handle_error(e, "Error fetching all clients")

    def _get_all_clients(self):
        """
        Executa busca de todos os clientes seguindo SRP.
        """
        return Client.objects.all().order_by("name")

    def _format_client_results(self, clients) -> list:
        """
        Formata resultados dos clientes seguindo SRP.
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


class ClientSearchRestView(BaseClientRestView):
    """
    REST view for client search.
    Implements name-based search functionality with pagination.
    """

    def get(self, request) -> JsonResponse:
        """
        Busca clientes por nome seguindo early return pattern.
        """
        try:
            # Guard clause: validação de query parameter
            query = request.GET.get("q", "").strip()
            if not query:
                return JsonResponse({"results": []})

            # Guard clause: query muito curta
            if len(query) < 3:
                return JsonResponse({"results": []})

            # Busca clientes seguindo princípios de clean code
            clients = self._search_clients(query)
            results = self._format_client_results(clients)

            return JsonResponse({"results": results})

        except Exception as e:
            return self.handle_error(e, "Error searching clients")

    def _search_clients(self, query: str):
        """
        Executa busca de clientes com filtros apropriados.
        SRP: responsabilidade única de buscar clientes.
        """
        return Client.objects.filter(Q(name__icontains=query)).order_by("name")[:10]

    def _format_client_results(self, clients) -> list:
        """
        Formata resultados da busca seguindo SRP.
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


class ClientContactsRestView(BaseClientRestView):
    """
    View REST para busca de contatos de um cliente.
    """

    def get(self, request, client_id: str) -> JsonResponse:
        """
        Busca contatos de um cliente específico.
        """
        try:
            # Guard clause: validação de client_id
            if not client_id:
                return JsonResponse({"error": "Client ID is required"}, status=400)

            # Busca cliente seguindo early return
            try:
                client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                return JsonResponse({"error": "Client not found"}, status=404)

            # Busca contatos do cliente
            contacts = self._get_client_contacts(client)
            results = self._format_contact_results(contacts)

            return JsonResponse({"results": results})

        except Exception as e:
            return self.handle_error(e, "Error fetching client contacts")

    def _get_client_contacts(self, client):
        """
        Busca contatos do cliente seguindo SRP.
        """
        return client.contacts.all().order_by("name")

    def _format_contact_results(self, contacts) -> list:
        """
        Formata resultados dos contatos seguindo SRP.
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


class ClientContactCreateRestView(BaseClientRestView):
    """
    REST view for creating client contacts.
    Follows SRP - single responsibility of orchestrating contact creation.
    """

    def post(self, request) -> JsonResponse:
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
            "notes": "Additional notes"        }
        """
        try:
            data = self._parse_json_body(request)
            logger.info(f"Received contact creation data: {data}")
            contact = self._create_contact(data)

            return JsonResponse(
                {
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
                },
                status=201,
            )

        except Exception as e:
            return self.handle_error(e, "Error creating contact")

    def _parse_json_body(self, request) -> Dict[str, Any]:
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


class ClientCreateRestView(BaseClientRestView):
    """
    REST view for creating new clients.
    Follows clean code principles and delegates to Django forms for validation.
    """

    def post(self, request) -> JsonResponse:
        """
        Create a new client following early return pattern.
        """
        try:
            # Parse JSON data with early return on error
            data = self._parse_json_data(request)

            # Create client with validation
            client = self._create_client(data)

            # Format successful response
            return JsonResponse(
                {
                    "success": True,
                    "client": self._format_client_data(client),
                    "message": f'Client "{client.name}" created successfully',
                },
                status=201,
            )

        except ValueError as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

        except Exception as e:
            return self.handle_error(e, "Error creating client")

    def _parse_json_data(self, request) -> Dict[str, Any]:
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
                error_messages.extend(
                    [f"{field}: {error}" for error in errors])
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
        }
