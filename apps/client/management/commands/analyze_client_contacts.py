"""Management command to analyze ClientContact duplicates and empty names."""

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.client.models import ClientContact
from apps.job.models import Job


class Command(BaseCommand):
    help = "Analyze ClientContact records for duplicates and empty names"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed information about each duplicate group",
        )

    def handle(self, *args, **options):
        verbose = options.get("verbose", False)

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("ClientContact State Analysis"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        # Analyze empty-name contacts
        self._analyze_empty_names(verbose)

        self.stdout.write("")

        # Analyze duplicates
        self._analyze_duplicates(verbose)

    def _analyze_empty_names(self, verbose):
        """Analyze ClientContact records with empty/whitespace names."""
        self.stdout.write(self.style.WARNING("\n1. EMPTY NAME ANALYSIS"))
        self.stdout.write("-" * 80)

        empty_name_contacts = ClientContact.objects.filter(
            name=""
        ) | ClientContact.objects.filter(name__regex=r"^\s+$")
        count = empty_name_contacts.count()

        self.stdout.write(f"Total contacts with empty/whitespace names: {count}")

        if count > 0 and verbose:
            self.stdout.write("\nSample records (first 10):")
            for contact in empty_name_contacts[:10]:
                self.stdout.write(f"  - ID: {contact.id}")
                self.stdout.write(f"    Client: {contact.client.name}")
                self.stdout.write(
                    f"    Name: '{contact.name}' (length: {len(contact.name)})"
                )
                self.stdout.write(f"    Email: {contact.email or 'None'}")

                # Check if any jobs reference this contact
                job_count = Job.objects.filter(contact=contact).count()
                if job_count > 0:
                    self.stdout.write(f"    ⚠️  Referenced by {job_count} jobs")
                self.stdout.write("")

    def _analyze_duplicates(self, verbose):
        """Analyze duplicate ClientContact records (same client + name)."""
        self.stdout.write(self.style.WARNING("\n2. DUPLICATE CONTACT ANALYSIS"))
        self.stdout.write("-" * 80)

        # Find all (client, name) combinations with duplicates
        duplicates = (
            ClientContact.objects.values("client", "name")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
            .order_by("-count")
        )

        total_duplicate_groups = duplicates.count()
        self.stdout.write(
            f"Total duplicate (client, name) combinations: {total_duplicate_groups}"
        )

        if total_duplicate_groups == 0:
            self.stdout.write(self.style.SUCCESS("✅ No duplicates found!"))
            return

        # Calculate total duplicate records
        total_duplicate_records = sum(d["count"] - 1 for d in duplicates)
        self.stdout.write(
            f"Total duplicate records to be merged: {total_duplicate_records}"
        )

        if verbose:
            self.stdout.write("\nTop 10 duplicate groups:")
            for i, dup in enumerate(duplicates[:10], 1):
                client_id = dup["client"]
                name = dup["name"]
                count = dup["count"]

                # Get the client
                from apps.client.models import Client

                client = Client.objects.get(id=client_id)

                self.stdout.write(f"\n{i}. Client: {client.name} (ID: {client.id})")
                self.stdout.write(f"   Contact Name: '{name}'")
                self.stdout.write(f"   Duplicate Count: {count}")

                # Show details of each duplicate
                contacts = ClientContact.objects.filter(
                    client_id=client_id, name=name
                ).order_by("-created_at")

                for contact in contacts[:5]:  # Show first 5
                    self.stdout.write(f"     - ID: {contact.id}")
                    self.stdout.write(f"       Email: {contact.email or 'None'}")
                    self.stdout.write(f"       Created: {contact.created_at}")

                    # Check job references
                    job_count = Job.objects.filter(contact=contact).count()
                    if job_count > 0:
                        self.stdout.write(f"       Jobs: {job_count}")

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("SUMMARY"))
        self.stdout.write("=" * 80)

        empty_count = (
            ClientContact.objects.filter(name="")
            | ClientContact.objects.filter(name__regex=r"^\s+$")
        ).count()

        self.stdout.write(f"Empty/whitespace name contacts: {empty_count}")
        self.stdout.write(
            f"Duplicate (client, name) combinations: {total_duplicate_groups}"
        )
        self.stdout.write(
            f"Total duplicate records to be removed: {total_duplicate_records}"
        )
        self.stdout.write(
            f"Total records after cleanup: {ClientContact.objects.count() - empty_count - total_duplicate_records}"
        )
