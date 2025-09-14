"""
Client REST Views

REST views for the Client module following clean code principles:
- SRP (Single Responsibility Principle)
- Early return and guard clauses
- Delegation to service layer
- Views as orchestrators only
"""

import logging
from typing import Any, Dict

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.client.models import Client
from apps.client.serializers import (
    ClientContactCreateRequestSerializer,
    ClientContactCreateResponseSerializer,
    ClientContactResponseSerializer,
    ClientCreateRequestSerializer,
    ClientCreateResponseSerializer,
    ClientDetailResponseSerializer,
    ClientDuplicateErrorResponseSerializer,
    ClientErrorResponseSerializer,
    ClientListResponseSerializer,
    ClientNameOnlySerializer,
    ClientSearchResponseSerializer,
    ClientUpdateRequestSerializer,
    ClientUpdateResponseSerializer,
    JobContactResponseSerializer,
)
from apps.client.services.client_rest_service import ClientRestService

logger = logging.getLogger(__name__)


@extend_schema_view(
    get=extend_schema(
        summary="List all clients",
        description="Returns a list of all clients with basic information (id and name) for dropdowns and search.",
        responses={
            200: ClientNameOnlySerializer(many=True),
            500: ClientErrorResponseSerializer,
        },
        tags=["Clients"],
    )
)
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
            clients_data = ClientRestService.get_all_clients()
            return Response(clients_data)
        except Exception as e:
            logger.error(f"Error fetching all clients: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error fetching all clients", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    get=extend_schema(
        summary="Search clients",
        parameters=[
            OpenApiParameter(
                name="q",
                location=OpenApiParameter.QUERY,
                required=False,
                description="Search query (min 3 chars, prefix match)",
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="limit",
                location=OpenApiParameter.QUERY,
                required=False,
                description="Max results (default 10, max 50)",
                type=OpenApiTypes.INT,
            ),
        ],
        responses={
            200: ClientSearchResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
        tags=["Clients"],
    )
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
            query = (request.GET.get("q") or "").strip()

            if not query or len(query) < 3:
                empty = {"results": []}
                serializer = ClientSearchResponseSerializer(data=empty)
                serializer.is_valid(raise_exception=True)
                return Response(serializer.data)

            # limit from query, with a sensible cap
            try:
                limit = int(request.GET.get("limit", 10))
            except ValueError:
                limit = 10
            limit = max(1, min(limit, 50))

            results = ClientRestService.search_clients(query, limit)
            payload = {"results": results}
            serializer = ClientSearchResponseSerializer(data=payload)
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


@extend_schema_view(
    get=extend_schema(
        summary="Get client details",
        description="Retrieve detailed information for a specific client.",
        parameters=[
            OpenApiParameter(
                name="client_id",
                location=OpenApiParameter.PATH,
                description="UUID of the client",
                required=True,
                type=OpenApiTypes.UUID,
            )
        ],
        responses={
            200: ClientDetailResponseSerializer,
            404: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
        tags=["Clients"],
    )
)
class ClientRetrieveRestView(APIView):
    """
    REST view for retrieving a specific client by ID.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ClientDetailResponseSerializer

    def get(self, request: Request, client_id: str) -> Response:
        """
        Retrieves detailed information for a specific client.
        """
        try:
            client_data = ClientRestService.get_client_by_id(client_id)
            return Response(client_data)
        except ValueError as e:
            error_serializer = ClientErrorResponseSerializer(data={"error": str(e)})
            error_serializer.is_valid(raise_exception=True)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving client {client_id}: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error retrieving client", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    put=extend_schema(
        summary="Update client",
        description="Update an existing client's information.",
        parameters=[
            OpenApiParameter(
                name="client_id",
                location=OpenApiParameter.PATH,
                description="UUID of the client",
                required=True,
                type=OpenApiTypes.UUID,
            )
        ],
        request=ClientUpdateRequestSerializer,
        responses={
            200: ClientUpdateResponseSerializer,
            400: ClientErrorResponseSerializer,
            404: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
        tags=["Clients"],
    ),
    patch=extend_schema(
        summary="Partially update client",
        description="Partially update an existing client's information.",
        parameters=[
            OpenApiParameter(
                name="client_id",
                location=OpenApiParameter.PATH,
                description="UUID of the client",
                required=True,
                type=OpenApiTypes.UUID,
            )
        ],
        request=ClientUpdateRequestSerializer,
        responses={
            200: ClientUpdateResponseSerializer,
            400: ClientErrorResponseSerializer,
            404: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
        tags=["Clients"],
    ),
)
class ClientUpdateRestView(APIView):
    """
    REST view for updating client information.
    Supports both PUT (full update) and PATCH (partial update).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ClientUpdateResponseSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method in ["PUT", "PATCH"]:
            return ClientUpdateRequestSerializer
        return ClientUpdateResponseSerializer

    def put(self, request: Request, client_id: str) -> Response:
        """
        Full update of client information.
        """
        return self._update_client(request, client_id, partial=False)

    def patch(self, request: Request, client_id: str) -> Response:
        """
        Partial update of client information.
        """
        return self._update_client(request, client_id, partial=True)

    def _update_client(
        self, request: Request, client_id: str, partial: bool = True
    ) -> Response:
        """
        Common method for handling client updates.
        """
        try:
            # Validate input data
            input_serializer = ClientUpdateRequestSerializer(
                data=request.data, partial=partial
            )
            if not input_serializer.is_valid():
                error_serializer = ClientErrorResponseSerializer(
                    data={"error": f"Invalid input data: {input_serializer.errors}"}
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            validated_data = input_serializer.validated_data
            updated_client = ClientRestService.update_client(client_id, validated_data)

            # Format response using the service method
            client_data = ClientRestService._format_client_detail(updated_client)
            response_data = {
                "success": True,
                "client": client_data,
                "message": f'Client "{updated_client.name}" updated successfully',
            }

            response_serializer = ClientUpdateResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data)

        except ValueError as e:
            # Handle not found and validation errors
            if "not found" in str(e).lower():
                error_serializer = ClientErrorResponseSerializer(data={"error": str(e)})
                error_serializer.is_valid(raise_exception=True)
                return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)
            else:
                error_serializer = ClientErrorResponseSerializer(data={"error": str(e)})
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Error updating client {client_id}: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error updating client", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    get=extend_schema(
        summary="Get client contacts",
        description="Retrieve all contacts for a specific client.",
        parameters=[
            OpenApiParameter(
                name="client_id",
                location=OpenApiParameter.PATH,
                description="UUID of the client",
                required=True,
                type=OpenApiTypes.UUID,
            )
        ],
        responses={
            200: ClientContactResponseSerializer,
            400: ClientErrorResponseSerializer,
            404: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
        tags=["Clients"],
    )
)
class ClientContactsRestView(APIView):
    """
    REST view for fetching contacts of a client.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ClientContactResponseSerializer

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

            results = ClientRestService.get_client_contacts(client_id)
            response_data = {"results": results}
            serializer = ClientContactResponseSerializer(data=response_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data)

        except ValueError as e:
            error_serializer = ClientErrorResponseSerializer(data={"error": str(e)})
            error_serializer.is_valid(raise_exception=True)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching client contacts: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error fetching client contacts", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    post=extend_schema(
        summary="Create a new client contact",
        request=ClientContactCreateRequestSerializer,
        responses={
            201: ClientContactCreateResponseSerializer,
            400: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
    )
)
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

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance for the request for OpenAPI compatibility"""
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

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
            contact = ClientRestService.create_client_contact(validated_data)

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

        except ValueError as e:
            error_serializer = ClientErrorResponseSerializer(data={"error": str(e)})
            error_serializer.is_valid(raise_exception=True)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating contact: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error creating contact", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    post=extend_schema(
        summary="Create a new client",
        description="Creates a new client in Xero first, then syncs locally. Requires valid Xero authentication.",
        request=ClientCreateRequestSerializer,
        responses={
            201: ClientCreateResponseSerializer,
            400: ClientErrorResponseSerializer,
            401: ClientErrorResponseSerializer,
            409: ClientDuplicateErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
        tags=["Clients"],
    )
)
class ClientCreateRestView(APIView):
    """
    REST view for creating new clients.
    Follows clean code principles and delegates to service layer.
    Creates client in Xero first, then syncs locally.
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
            created_client = ClientRestService.create_client(validated_data)

            response_data = {
                "success": True,
                "client": self._format_client_data(created_client),
                "message": f'Client "{created_client.name}" created successfully',
            }

            response_serializer = ClientCreateResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            logger.error(
                f"Error during client creation: {e} | Request data: {request.data}"
            )
            # Handle duplicate client error
            if "already exists in Xero" in str(e):
                # Extract client name from error message
                error_msg = str(e)
                if "Client '" in error_msg and "' already exists" in error_msg:
                    name = error_msg.split("Client '")[1].split("' already exists")[0]
                    duplicate_error_data = {
                        "error": error_msg,
                        "existing_client": {
                            "name": name,
                            "xero_contact_id": (
                                error_msg.split("ID: ")[-1]
                                if "ID: " in error_msg
                                else ""
                            ),
                        },
                    }
                    error_serializer = ClientDuplicateErrorResponseSerializer(
                        data=duplicate_error_data
                    )
                    error_serializer.is_valid(raise_exception=True)
                    return Response(
                        error_serializer.data, status=status.HTTP_409_CONFLICT
                    )

            # Handle validation errors
            if "authentication required" in str(e).lower():
                error_serializer = ClientErrorResponseSerializer(data={"error": str(e)})
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_401_UNAUTHORIZED
                )

            # Other validation errors
            error_serializer = ClientErrorResponseSerializer(data={"error": str(e)})
            error_serializer.is_valid(raise_exception=True)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating client: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error creating client", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
            "last_invoice_date": (
                client.get_last_invoice_date().strftime("%d/%m/%Y")
                if client.get_last_invoice_date()
                else ""
            ),
            "total_spend": f"${client.get_total_spend():,.2f}",
        }


@extend_schema_view(
    get=extend_schema(
        summary="Get job contact",
        description="Retrieve contact information for a specific job.",
        parameters=[
            OpenApiParameter(
                name="job_id",
                location=OpenApiParameter.PATH,
                description="UUID of the job",
                required=True,
                type=OpenApiTypes.UUID,
            )
        ],
        responses={
            200: JobContactResponseSerializer,
            404: ClientErrorResponseSerializer,
            500: ClientErrorResponseSerializer,
        },
        tags=["Clients"],
    )
)
class JobContactRestView(APIView):
    """
    REST view for retrieving contact information for a job.
    Returns the contact associated with a specific job.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = JobContactResponseSerializer

    def get(self, request: Request, job_id: str) -> Response:
        """
        Retrieves contact information for a specific job.
        """
        try:
            # Guard clause: validate job_id
            if not job_id:
                error_serializer = ClientErrorResponseSerializer(
                    data={"error": "Job ID is required"}
                )
                error_serializer.is_valid(raise_exception=True)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            contact_data = ClientRestService.get_job_contact(job_id)
            serializer = JobContactResponseSerializer(data=contact_data)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data)

        except ValueError as e:
            error_serializer = ClientErrorResponseSerializer(data={"error": str(e)})
            error_serializer.is_valid(raise_exception=True)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving job contact for job {job_id}: {str(e)}")
            error_serializer = ClientErrorResponseSerializer(
                data={"error": "Error retrieving job contact", "details": str(e)}
            )
            error_serializer.is_valid(raise_exception=True)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
