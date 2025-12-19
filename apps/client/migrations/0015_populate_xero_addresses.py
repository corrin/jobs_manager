# Generated migration to backfill SupplierPickupAddress from Xero STREET addresses

from django.db import migrations


def create_xero_addresses(apps, schema_editor):
    """Create SupplierPickupAddress records from Client raw_json Xero data."""
    Client = apps.get_model("client", "Client")
    SupplierPickupAddress = apps.get_model("client", "SupplierPickupAddress")

    created_count = 0
    for client in Client.objects.exclude(raw_json__isnull=True):
        raw_json = client.raw_json
        if not isinstance(raw_json.get("_addresses"), list):
            continue

        for address_entry in raw_json.get("_addresses", []):
            if not isinstance(address_entry, dict):
                continue
            if address_entry.get("_address_type") != "STREET":
                continue

            # Extract individual address components
            line1 = address_entry.get("_address_line1") or ""
            line2 = address_entry.get("_address_line2") or ""
            line3 = address_entry.get("_address_line3") or ""
            line4 = address_entry.get("_address_line4") or ""
            city = address_entry.get("_city") or ""

            # Combine address lines for street field
            street_parts = [p for p in [line1, line2, line3, line4] if p]
            street = ", ".join(street_parts)

            # Only create if we have both street and city (required fields)
            if street and city:
                _, created = SupplierPickupAddress.objects.get_or_create(
                    client=client,
                    name="Xero Address",
                    defaults={
                        "street": street,
                        "city": city,
                        "state": address_entry.get("_region") or None,
                        "postal_code": address_entry.get("_postal_code") or None,
                        "country": address_entry.get("_country") or "New Zealand",
                        "is_primary": True,
                    },
                )
                if created:
                    created_count += 1
            break  # Only process first STREET address

    print(f"\n  Created {created_count} Xero Address records")


class Migration(migrations.Migration):
    dependencies = [
        ("client", "0014_add_suburb_to_pickup_address"),
    ]

    operations = [
        migrations.RunPython(create_xero_addresses, migrations.RunPython.noop),
    ]
