"""
Address Validation Views

Provides address cleaning/validation using Google Address Validation API.
"""

import logging
import os

import requests
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class AddressValidateView(APIView):
    """
    Validate and clean an address using Google Address Validation API.

    POST /api/clients/addresses/validate/
    Body: {"address": "123 Main St Melbourne"}

    Returns candidate addresses with structured components.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Freetext address to validate",
                    },
                },
                "required": ["address"],
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "formatted_address": {"type": "string"},
                                "street": {"type": "string"},
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                                "postal_code": {"type": "string"},
                                "country": {"type": "string"},
                                "google_place_id": {"type": "string"},
                                "latitude": {"type": "number"},
                                "longitude": {"type": "number"},
                            },
                        },
                    },
                },
            },
            400: {"description": "Missing or invalid address"},
            503: {"description": "Google API unavailable or not configured"},
        },
    )
    def post(self, request: Request) -> Response:
        """Validate an address and return structured candidates."""
        address = request.data.get("address", "").strip()

        if not address:
            return Response(
                {"error": "Address is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not configured")
            return Response(
                {"error": "Address validation service not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            candidates = self._validate_with_google(address, api_key)
            return Response({"candidates": candidates})
        except Exception as exc:
            persist_app_error(exc)
            logger.exception("Address validation failed")
            return Response(
                {"error": "Address validation failed"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    def _validate_with_google(self, address: str, api_key: str) -> list[dict]:
        """
        Call Google Address Validation API and return structured results.

        Uses the Address Validation API which returns detailed address components.
        See: https://developers.google.com/maps/documentation/address-validation
        """
        url = "https://addressvalidation.googleapis.com/v1:validateAddress"

        payload = {
            "address": {
                "addressLines": [address],
                "regionCode": "NZ",  # Default to New Zealand
            },
            "enableUspsCass": False,
        }

        response = requests.post(
            url,
            json=payload,
            params={"key": api_key},
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(
                f"Google Address Validation API error: {response.status_code} - {response.text}"
            )
            raise RuntimeError(f"Google API returned {response.status_code}")

        data = response.json()
        return self._parse_validation_result(data)

    def _parse_validation_result(self, data: dict) -> list[dict]:
        """Parse Google Address Validation API response into our format."""
        result = data.get("result", {})
        address_obj = result.get("address", {})
        geocode = result.get("geocode", {})

        # Extract place ID and coordinates
        place_id = geocode.get("placeId", "")
        location = geocode.get("location", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        # Extract components
        components = {}
        for component in address_obj.get("addressComponents", []):
            comp_type = component.get("componentType", "")
            text = component.get("componentName", {}).get("text", "")

            if comp_type == "street_number":
                components["street_number"] = text
            elif comp_type == "route":
                components["route"] = text
            elif comp_type == "locality":
                components["city"] = text
            elif comp_type == "administrative_area_level_1":
                components["state"] = text
            elif comp_type == "postal_code":
                components["postal_code"] = text
            elif comp_type == "country":
                components["country"] = text

        # Build street from number + route
        street_parts = []
        if components.get("street_number"):
            street_parts.append(components["street_number"])
        if components.get("route"):
            street_parts.append(components["route"])
        street = " ".join(street_parts)

        formatted = address_obj.get("formattedAddress", "")

        # Return as a single candidate (API returns one result)
        if formatted:
            return [
                {
                    "formatted_address": formatted,
                    "street": street,
                    "city": components.get("city", ""),
                    "state": components.get("state", ""),
                    "postal_code": components.get("postal_code", ""),
                    "country": components.get("country", "New Zealand"),
                    "google_place_id": place_id,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            ]
        return []
