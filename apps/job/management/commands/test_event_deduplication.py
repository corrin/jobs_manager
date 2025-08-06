"""
Management command to test event deduplication functionality.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from apps.accounts.models import Staff
from apps.client.models import Client
from apps.job.models import Job, JobEvent
from apps.job.services.job_rest_service import JobRestService

User = get_user_model()


class Command(BaseCommand):
    help = "Test event deduplication functionality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Clean up test data after running tests",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Starting Event Deduplication Tests"))

        # Setup test data
        self.setup_test_data()

        try:
            # Run all tests
            self.test_model_prevents_duplicates()
            self.test_create_safe_method()
            self.test_service_prevents_duplicates()
            self.test_different_users_same_event()
            self.test_automatic_events_not_affected()
            self.test_hash_generation()

            self.stdout.write(self.style.SUCCESS("✅ All tests passed successfully!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test failed: {e}"))
            raise

        finally:
            if options["cleanup"]:
                self.cleanup_test_data()

    def setup_test_data(self):
        """Set up test data."""
        self.stdout.write("Setting up test data...")

        # Create test user
        self.user, created = Staff.objects.get_or_create(
            email="test_dedup@example.com",
            defaults={"first_name": "Test", "last_name": "User"},
        )
        if created:
            self.user.set_password("testpass123")
            self.user.save()

        # Create second test user
        self.user2, created = Staff.objects.get_or_create(
            email="test_dedup2@example.com",
            defaults={"first_name": "Test2", "last_name": "User2"},
        )
        if created:
            self.user2.set_password("testpass123")
            self.user2.save()

        # Create test client
        from django.utils import timezone

        self.client_obj, created = Client.objects.get_or_create(
            name="Test Dedup Client",
            defaults={
                "email": "client_dedup@example.com",
                "xero_last_modified": timezone.now(),
            },
        )

        # Create test job
        self.job, created = Job.objects.get_or_create(
            name="Test Dedup Job",
            client=self.client_obj,
            defaults={"created_by": self.user},
        )

        self.stdout.write("✅ Test data setup complete")

    def test_model_prevents_duplicates(self):
        """Test that the model prevents duplicate manual events."""
        self.stdout.write("Testing model duplicate prevention...")

        # Create first event
        event1 = JobEvent.objects.create(
            job=self.job,
            staff=self.user,
            description="Model test event",
            event_type="manual_note",
        )
        assert event1.dedup_hash, "Dedup hash should be generated"

        # Attempt to create duplicate — should raise ValidationError
        try:
            JobEvent.objects.create(
                job=self.job,
                staff=self.user,
                description="Model test event",
                event_type="manual_note",
            )
            # if we get here, no exception was raised
            raise AssertionError("Expected ValidationError for duplicate manual_note")
        except ValidationError as e:
            msgs = e.messages
            # check that both our custom and Django's messages are present
            assert any(
                "similar manual event" in m.lower() for m in msgs
            ), f"Missing custom message: {msgs}"
            assert any(
                "already exists" in m.lower() for m in msgs
            ), f"Missing unique-constraint message: {msgs}"

        self.stdout.write("✅ Model duplicate prevention works")

    def test_create_safe_method(self):
        """Test that create_safe method handles duplicates gracefully."""
        self.stdout.write("Testing create_safe method...")

        # Create first event
        event1, created1 = JobEvent.create_safe(
            job=self.job,
            staff=self.user,
            description="Safe method test event",
            event_type="manual_note",
        )

        assert created1, "First event should be created"

        # Try to create duplicate
        event2, created2 = JobEvent.create_safe(
            job=self.job,
            staff=self.user,
            description="Safe method test event",  # Same description
            event_type="manual_note",
        )

        assert not created2, "Second event should not be created"
        assert event1.id == event2.id, "Should return existing event"

        self.stdout.write("✅ create_safe method works")

    def test_service_prevents_duplicates(self):
        """Test that the service layer prevents duplicate events."""
        self.stdout.write("Testing service layer duplicate prevention...")

        description = "Service test event"

        # Create first event
        result1 = JobRestService.add_job_event(self.job.id, description, self.user)

        assert result1["success"], "First event should succeed"
        assert not result1.get(
            "duplicate_prevented", False
        ), "First event should not be marked as duplicate"

        # Try to create duplicate immediately
        result2 = JobRestService.add_job_event(self.job.id, description, self.user)

        assert result2["success"], "Second event should succeed"
        assert result2.get(
            "duplicate_prevented", False
        ), "Second event should be marked as duplicate"

        # Verify only one event exists in database
        events = JobEvent.objects.filter(
            job=self.job,
            staff=self.user,
            description=description,
            event_type="manual_note",
        )

        assert events.count() == 1, f"Expected 1 event, found {events.count()}"

        self.stdout.write("✅ Service layer duplicate prevention works")

    def test_different_users_same_event(self):
        """Test that different users can create events with same description."""
        self.stdout.write("Testing different users with same event description...")

        description = "Multi-user test event"

        # Event from first user
        result1 = JobRestService.add_job_event(self.job.id, description, self.user)
        assert result1["success"], "First user event should succeed"

        # Event from second user (should be allowed)
        result2 = JobRestService.add_job_event(self.job.id, description, self.user2)
        assert result2["success"], "Second user event should succeed"
        assert not result2.get(
            "duplicate_prevented", False
        ), "Second user event should not be marked as duplicate"

        # Verify both events exist
        events = JobEvent.objects.filter(
            job=self.job, description=description, event_type="manual_note"
        )
        assert events.count() == 2, f"Expected 2 events, found {events.count()}"

        self.stdout.write("✅ Different users can create same event")

    def test_automatic_events_not_affected(self):
        """Test that automatic events are not affected by deduplication."""
        self.stdout.write("Testing automatic events are not affected...")

        # Create multiple automatic events with same description
        for i in range(3):
            JobEvent.objects.create(
                job=self.job,
                staff=self.user,
                description="Status changed to in_progress",
                event_type="status_changed",
            )

        # All should be created successfully
        events = JobEvent.objects.filter(
            job=self.job,
            description="Status changed to in_progress",
            event_type="status_changed",
        )
        assert (
            events.count() == 3
        ), f"Expected 3 automatic events, found {events.count()}"

        self.stdout.write("✅ Automatic events are not affected by deduplication")

    def test_hash_generation(self):
        """Test that dedup_hash is generated correctly."""
        self.stdout.write("Testing hash generation...")

        event = JobEvent.objects.create(
            job=self.job,
            staff=self.user,
            description="Hash generation test",
            event_type="manual_note",
        )

        # Hash should be generated
        assert event.dedup_hash is not None, "Hash should be generated"
        assert (
            len(event.dedup_hash) == 32
        ), f"Hash should be 32 chars, got {len(event.dedup_hash)}"

        # Hash should be consistent
        expected_hash = event._generate_dedup_hash()
        assert event.dedup_hash == expected_hash, "Hash should be consistent"

        self.stdout.write("✅ Hash generation works correctly")

    def cleanup_test_data(self):
        """Clean up test data."""
        self.stdout.write("Cleaning up test data...")

        # Delete test events
        JobEvent.objects.filter(job=self.job).delete()

        # Delete test job
        self.job.delete()

        # Delete test client
        self.client_obj.delete()

        # Delete test users
        self.user.delete()
        self.user2.delete()

        self.stdout.write("✅ Test data cleaned up")
