"""
Geocode SupplierPickupAddress records using Google Address Validation API.

Usage:
    python manage.py geocode_addresses              # Geocode addresses missing lat/lng
    python manage.py geocode_addresses --dry-run   # Show what would be geocoded
    python manage.py geocode_addresses --limit 10  # Only process 10 addresses
    python manage.py geocode_addresses --all       # Re-geocode all addresses
"""

import logging
import time

from django.core.management.base import BaseCommand

from apps.client.models import SupplierPickupAddress
from apps.client.services.geocoding_service import (
    GeocodingError,
    GeocodingNotConfiguredError,
    geocode_address,
    get_api_key,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Geocode SupplierPickupAddress records using Google Address Validation API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be geocoded without making changes",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of addresses to process",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Re-geocode all addresses, not just those missing lat/lng",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]
        geocode_all = options["all"]

        # Check API key upfront
        try:
            api_key = get_api_key()
        except GeocodingNotConfiguredError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        # Build queryset
        if geocode_all:
            queryset = SupplierPickupAddress.objects.filter(is_active=True)
        else:
            # Only addresses missing latitude
            queryset = SupplierPickupAddress.objects.filter(
                is_active=True,
                latitude__isnull=True,
            )

        if limit:
            queryset = queryset[:limit]

        addresses = list(queryset)
        total = len(addresses)

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No addresses to geocode"))
            return

        self.stdout.write(f"Found {total} addresses to geocode")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        success_count = 0
        error_count = 0

        for i, address in enumerate(addresses, 1):
            freetext = self._build_freetext_address(address)
            self.stdout.write(f"\n[{i}/{total}] {address.client.name}")
            self.stdout.write(f"  Input: {freetext}")

            if dry_run:
                continue

            try:
                result = geocode_address(freetext, api_key)
                if result:
                    address.latitude = result.latitude
                    address.longitude = result.longitude
                    address.google_place_id = result.google_place_id

                    # Optionally update other fields if they were empty
                    if not address.suburb and result.suburb:
                        address.suburb = result.suburb
                    if not address.postal_code and result.postal_code:
                        address.postal_code = result.postal_code

                    address.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  -> {result.latitude}, {result.longitude}"
                        )
                    )
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING("  -> No result returned"))
                    error_count += 1

                # Rate limiting - be nice to Google API
                time.sleep(0.2)

            except GeocodingError as exc:
                self.stdout.write(self.style.ERROR(f"  -> Error: {exc}"))
                error_count += 1
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  -> Unexpected error: {exc}"))
                error_count += 1
                logger.exception(f"Failed to geocode address {address.id}")

        self.stdout.write("")
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully geocoded: {success_count}")
            )
            if error_count:
                self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))

    def _build_freetext_address(self, address: SupplierPickupAddress) -> str:
        """Build a freetext address string from address components."""
        parts = [
            address.street,
            address.suburb,
            address.city,
            address.postal_code,
            address.country,
        ]
        return ", ".join(p for p in parts if p)
