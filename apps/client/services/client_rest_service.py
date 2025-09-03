"""
Client REST Service Layer

Following SRP (Single Responsibility Principle) and clean code guidelines.
All business logic for Client REST operations should be implemented here.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List
from uuid import UUID

from django.db import transaction
from django.db.models import DecimalField, Max, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from xero_python.accounting import AccountingApi

from apps.client.forms import ClientForm
from apps.client.models import Client, ClientContact
from apps.workflow.api.xero.sync import sync_clients
from apps.workflow.api.xero.xero import api_client, get_tenant_id, get_valid_token
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class ClientRestService:
    """
    Service layer for Client REST operations.
    Implements all business rules related to Client manipulation via REST API.
    """

    @staticmethod
    def get_all_clients() -> List[Dict[str, Any]]:
        """
        Retrieves all clients with basic information for dropdowns.

        Returns:
            List of client dictionaries with id and name
        """
        try:
            clients = Client.objects.all().order_by("name")
            return [
                {
                    "id": str(client.id),
                    "name": client.name,
                }
                for client in clients
            ]
        except Exception as e:
            persist_app_error(e)
            raise

    @staticmethod
    def search_clients(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Searches clients by name with enhanced data.

        Args:
            query: Search query (minimum 3 characters)
            limit: Maximum results to return (capped at 50)

        Returns:
            List of client dictionaries with detailed information

        Raises:
            ValueError: If query is too short
        """
        try:
            # Guard clause - validate query length
            if not query or len(query.strip()) < 3:
                return []

            # Sanitize and limit
            query = query.strip()
            limit = max(1, min(limit, 50))

            # Execute optimized search
            clients = ClientRestService._execute_client_search(query, limit)
            return ClientRestService._format_client_search_results(clients)

        except Exception as e:
            persist_app_error(e)
            raise

    @staticmethod
    def get_client_by_id(client_id: UUID) -> Dict[str, Any]:
        """
        Retrieves a specific client by ID with full details.

        Args:
            client_id: Client UUID

        Returns:
            Dict with complete client information

        Raises:
            ValueError: If client not found
        """
        try:
            client = Client.objects.get(id=client_id)
            return ClientRestService._format_client_detail(client)
        except Client.DoesNotExist:
            raise ValueError(f"Client with id {client_id} not found")
        except Exception as e:
            persist_app_error(e)
            raise

    @staticmethod
    def create_client(data: Dict[str, Any]) -> Client:
        """
        Creates a new client in Xero first, then syncs locally.

        Args:
            data: Client creation data

        Returns:
            Created Client instance

        Raises:
            ValueError: If validation fails or Xero sync fails
        """
        try:
            # Guard clause - validate required fields
            if not data.get("name"):
                raise ValueError("Client name is required")

            # Validate using Django form
            form = ClientForm(data)
            if not form.is_valid():
                error_messages = []
                for field, errors in form.errors.items():
                    error_messages.extend([f"{field}: {error}" for error in errors])
                raise ValueError("; ".join(error_messages))

            # Check Xero authentication
            token = get_valid_token()
            if not token:
                raise ValueError("Xero authentication required")

            # Create in Xero first
            client = ClientRestService._create_client_in_xero(form.cleaned_data)
            return client

        except Exception as e:
            persist_app_error(e)
            raise

    @staticmethod
    def update_client(client_id: UUID, data: Dict[str, Any]) -> Client:
        """
        Updates an existing client.
        If client is synced with Xero, updates Xero first then syncs locally.

        Args:
            client_id: Client UUID
            data: Updated client data

        Returns:
            Updated Client instance

        Raises:
            ValueError: If client not found or validation fails
        """
        try:
            client = get_object_or_404(Client, id=client_id)

            # Guard clause - validate required fields
            if not data.get("name") and not client.name:
                raise ValueError("Client name is required")

            # Store xero_contact_id before form validation
            original_xero_contact_id = client.xero_contact_id

            # Validate using Django form for basic validation (without modifying instance)
            form = ClientForm(data)  # Don't pass instance to avoid modification
            if not form.is_valid():
                error_messages = []
                for field, errors in form.errors.items():
                    error_messages.extend([f"{field}: {error}" for error in errors])
                raise ValueError("; ".join(error_messages))

            # DEBUG: Log client state after form validation
            logger.info(
                f"Client data after form validation: xero_contact_id={original_xero_contact_id}",
                extra={
                    "client_id": str(client.id),
                    "original_xero_contact_id": original_xero_contact_id,
                    "operation": "update_client_debug_after_form",
                },
            )

            # Check if client is synced with Xero
            if original_xero_contact_id:
                # Update in Xero first, then sync locally
                updated_client = ClientRestService._update_client_in_xero(client, data)
                logger.info(
                    f"Client {updated_client.id} updated in Xero and synced locally",
                    extra={
                        "client_id": str(updated_client.id),
                        "client_name": updated_client.name,
                        "xero_contact_id": updated_client.xero_contact_id,
                        "operation": "update_client_xero_sync",
                    },
                )
                return updated_client
            else:
                # Local-only update for clients not synced with Xero
                with transaction.atomic():
                    client = form.save(commit=False)
                    client.xero_last_modified = timezone.now()
                    client.save()

                    logger.info(
                        f"Client {client.id} updated locally (no Xero sync)",
                        extra={
                            "client_id": str(client.id),
                            "client_name": client.name,
                            "operation": "update_client_local_only",
                        },
                    )

                return client

        except Exception as e:
            persist_app_error(e)
            raise

    @staticmethod
    def get_client_contacts(client_id: UUID) -> List[Dict[str, Any]]:
        """
        Retrieves all contacts for a specific client.

        Args:
            client_id: Client UUID

        Returns:
            List of contact dictionaries

        Raises:
            ValueError: If client not found
        """
        try:
            client = get_object_or_404(Client, id=client_id)
            contacts = client.contacts.all().order_by("name")

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

        except Exception as e:
            persist_app_error(e)
            raise

    @staticmethod
    def create_client_contact(data: Dict[str, Any]) -> ClientContact:
        """
        Creates a new client contact.

        Args:
            data: Contact creation data

        Returns:
            Created ClientContact instance

        Raises:
            ValueError: If validation fails
        """
        try:
            # Guard clauses - validate required fields
            if not data.get("client_id"):
                raise ValueError("client_id is required")

            if not data.get("name") or not data["name"].strip():
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

            logger.info(
                f"Contact {contact.id} created for client {client.id}",
                extra={
                    "contact_id": str(contact.id),
                    "client_id": str(client.id),
                    "operation": "create_client_contact",
                },
            )

            return contact

        except Exception as e:
            persist_app_error(e)
            raise

    @staticmethod
    def _execute_client_search(query: str, limit: int):
        """
        Executes client search with appropriate filters and annotations.
        """
        output = DecimalField(max_digits=12, decimal_places=2)

        return (
            Client.objects.filter(name__startswith=query)  # Index-friendly
            .annotate(
                last_invoice_date=Max("invoice__date"),
                total_spend=Coalesce(
                    Sum(
                        "invoice__total_excl_tax",
                        output_field=output,
                    ),
                    Value(Decimal("0.00")),
                    output_field=output,
                ),
            )
            .defer("raw_json")  # Not needed for search results
            .only(
                "id",
                "name",
                "email",
                "phone",
                "address",
                "is_account_customer",
                "xero_contact_id",
            )
            .order_by("name")[:limit]
        )

    @staticmethod
    def _format_client_search_results(clients) -> List[Dict[str, Any]]:
        """
        Formats client search results for API response.
        """
        formatted = []
        for client in clients:
            # Guard None for date
            date_str = (
                client.last_invoice_date.strftime("%d/%m/%Y")
                if client.last_invoice_date
                else ""
            )
            formatted.append(
                {
                    "id": str(client.id),
                    "name": client.name,
                    "email": client.email or "",
                    "phone": client.phone or "",
                    "address": client.address or "",
                    "is_account_customer": client.is_account_customer,
                    "xero_contact_id": client.xero_contact_id or "",
                    "last_invoice_date": date_str,
                    "total_spend": f"${client.total_spend:,.2f}",
                }
            )
        return formatted

    @staticmethod
    def _format_client_detail(client: Client) -> Dict[str, Any]:
        """
        Formats complete client details for API response.
        """
        return {
            "id": str(client.id),
            "name": client.name,
            "email": client.email or "",
            "phone": client.phone or "",
            "address": client.address or "",
            "is_account_customer": client.is_account_customer,
            "is_supplier": client.is_supplier,
            "xero_contact_id": client.xero_contact_id or "",
            "xero_tenant_id": client.xero_tenant_id or "",
            "primary_contact_name": client.primary_contact_name or "",
            "primary_contact_email": client.primary_contact_email or "",
            "additional_contact_persons": client.additional_contact_persons or [],
            "all_phones": client.all_phones or [],
            "xero_last_modified": client.xero_last_modified.isoformat()
            if client.xero_last_modified
            else None,
            "xero_last_synced": client.xero_last_synced.isoformat()
            if client.xero_last_synced
            else None,
            "xero_archived": client.xero_archived,
            "xero_merged_into_id": client.xero_merged_into_id or "",
            "merged_into": str(client.merged_into.id) if client.merged_into else None,
            "django_created_at": client.django_created_at.isoformat(),
            "django_updated_at": client.django_updated_at.isoformat(),
            "last_invoice_date": client.get_last_invoice_date().strftime("%d/%m/%Y")
            if client.get_last_invoice_date()
            else "",
            "total_spend": f"${client.get_total_spend():,.2f}",
        }

    @staticmethod
    def _create_client_in_xero(client_data: Dict[str, Any]) -> Client:
        """
        Creates client in Xero and syncs locally.
        """
        accounting_api = AccountingApi(api_client)
        xero_tenant_id = get_tenant_id()
        name = client_data["name"]

        # Check for duplicates in Xero
        existing_contacts = accounting_api.get_contacts(
            xero_tenant_id, where=f'Name="{name}"'
        )
        if existing_contacts and existing_contacts.contacts:
            xero_client = existing_contacts.contacts[0]
            xero_contact_id = getattr(xero_client, "contact_id", "")
            raise ValueError(
                f"Client '{name}' already exists in Xero with ID: {xero_contact_id}"
            )

        # Create new contact in Xero - sanitize None values
        contact_data = {
            "name": name,
            "emailAddress": client_data.get("email") or "",
            "phones": [
                {
                    "phoneType": "DEFAULT",
                    "phoneNumber": client_data.get("phone") or "",
                }
            ],
            "addresses": [
                {
                    "addressType": "STREET",
                    "addressLine1": client_data.get("address") or "",
                }
            ],
            "isCustomer": client_data.get("is_account_customer", True),
        }

        response = accounting_api.create_contacts(
            xero_tenant_id, contacts={"contacts": [contact_data]}
        )

        if not response or not hasattr(response, "contacts") or not response.contacts:
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
        logger.info(
            f"Client {created_client.id} created and synced from Xero",
            extra={
                "client_id": str(created_client.id),
                "client_name": created_client.name,
                "xero_contact_id": created_client.xero_contact_id,
                "operation": "create_client_in_xero",
            },
        )
        return created_client

    @staticmethod
    def _update_client_in_xero(client: Client, data: Dict[str, Any]) -> Client:
        """
        Updates client in Xero and syncs locally.
        """
        # Check Xero authentication
        token = get_valid_token()
        if not token:
            raise ValueError("Xero authentication required")

        accounting_api = AccountingApi(api_client)
        xero_tenant_id = get_tenant_id()

        # Prepare update data for Xero - sanitize None values
        name = data.get("name", client.name)
        email = data.get("email", client.email)
        phone = data.get("phone", client.phone)
        address = data.get("address", client.address)
        is_account_customer = data.get(
            "is_account_customer", client.is_account_customer
        )

        contact_data = {
            "contactID": client.xero_contact_id,  # Required for update
            "name": name,
            "emailAddress": email or "",
            "phones": [
                {
                    "phoneType": "DEFAULT",
                    "phoneNumber": phone or "",
                }
            ],
            "addresses": [
                {
                    "addressType": "STREET",
                    "addressLine1": address or "",
                }
            ],
            "isCustomer": is_account_customer,
        }

        try:
            # Update contact in Xero
            response = accounting_api.update_contact(
                xero_tenant_id,
                contact_id=client.xero_contact_id,
                contacts={"contacts": [contact_data]},
            )

            if (
                not response
                or not hasattr(response, "contacts")
                or not response.contacts
            ):
                raise ValueError("No contact data in Xero update response")

            if len(response.contacts) != 1:
                raise ValueError(
                    f"Expected 1 contact in update response, got {len(response.contacts)}"
                )

            # Sync updated data locally
            client_instances = sync_clients(response.contacts)
            if not client_instances:
                raise ValueError("Failed to sync updated client from Xero")

            updated_client = client_instances[0]

            logger.info(
                f"Client {updated_client.id} updated in Xero and synced locally",
                extra={
                    "client_id": str(updated_client.id),
                    "client_name": updated_client.name,
                    "xero_contact_id": updated_client.xero_contact_id,
                    "operation": "_update_client_in_xero",
                },
            )

            return updated_client

        except Exception as e:
            logger.error(f"Error updating client in Xero: {str(e)}")
            # If Xero update fails, fall back to local update with warning
            logger.warning(
                f"Xero update failed for client {client.id}, performing local update only"
            )

            # Preserve Xero fields during local fallback update
            xero_fields = {
                "xero_contact_id": client.xero_contact_id,
                "xero_tenant_id": client.xero_tenant_id,
                "raw_json": client.raw_json,
                "xero_last_synced": client.xero_last_synced,
                "xero_archived": client.xero_archived,
                "xero_merged_into_id": client.xero_merged_into_id,
                "merged_into": client.merged_into,
            }

            # Add preserved Xero fields to update data
            update_data = data.copy()
            for field, value in xero_fields.items():
                if field not in update_data:
                    update_data[field] = value

            # Perform local update as fallback
            form = ClientForm(update_data, instance=client)
            if form.is_valid():
                with transaction.atomic():
                    client = form.save(commit=False)
                    client.xero_last_modified = timezone.now()
                    client.save()

                    logger.info(
                        f"Client {client.id} updated locally as fallback",
                        extra={
                            "client_id": str(client.id),
                            "client_name": client.name,
                            "operation": "_update_client_in_xero_fallback",
                            "xero_error": str(e),
                        },
                    )

                return client
            else:
                # If both Xero and local update fail, raise the original Xero error
                raise ValueError(f"Xero update failed: {str(e)}")
