nimport os

import django
from django.core.management import call_command
from django.test import Client, TestCase
from dotenv import load_dotenv
from rest_framework import serializers
from rest_framework.test import APITestCase

from job.enums import JobPricingMethodology

from job.models import Job, JobFile, MaterialEntry, AdjustmentEntry

from timesheet.models import TimeEntry

from job.serializers import JobPricingSerializer, JobSerializer

django.setup()  # Force initialization
load_dotenv()


class SerializerFieldSyncTest(APITestCase):
    """Test that ensures all model fields are properly handled in serializers."""

    def get_model_fields(self, model_class):
        """Get direct fields from a model."""
        fields = []
        for field in model_class._meta.get_fields():
            if not field.is_relation:
                fields.append(
                    {
                        "name": field.name,
                        "type": field.__class__.__name__,
                        "model": model_class.__name__,
                    }
                )
        return fields

    def get_serializer_fields(self, serializer_class):
        """Get direct fields from a serializer."""
        serializer = serializer_class()
        fields = []
        for name, field in serializer.fields.items():
            fields.append(
                {
                    "name": name,
                    "type": field.__class__.__name__,
                    "source": getattr(field, "source", name),
                }
            )
            # If this is a nested serializer, get its fields too
            if isinstance(field, serializers.ModelSerializer):
                nested_fields = self.get_serializer_fields(field.__class__)
                fields.extend(
                    [
                        {
                            "name": f"{name}.{f['name']}",
                            "type": f["type"],
                            "source": f"{getattr(field, 'source', name)}.{f['source']}",
                        }
                        for f in nested_fields
                    ]
                )
        return fields

    def test_field_coverage(self):
        """Test for field coverage issues."""
        # Check JobFile fields
        jobfile_fields = self.get_model_fields(JobFile)

        # Get serializer fields that handle JobFile data
        serializer = JobSerializer()
        job_files_field = serializer.fields.get("job_files")

        if job_files_field and isinstance(job_files_field, serializers.DictField):
            print("\nJobFile Handling Issues:")
            print("------------------------")
            print(
                "JobFile is handled as a dict in job_files, but these fields need attention:"
            )
            for field in jobfile_fields:
                if field["name"] not in ["id", "job"]:  # Skip obvious fields
                    print(f"- {field['name']} ({field['type']})")
                    if field["name"] == "print_on_jobsheet":
                        print(
                            "  Note: Currently only handled in update() method, not declared in fields"
                        )

        # Check JobPricing serializer for issues
        pricing_serializer = JobPricingSerializer()
        field_counts = {}
        for name, _ in pricing_serializer.fields.items():
            field_counts[name] = field_counts.get(name, 0) + 1

        print("\nJobPricing Serializer Issues:")
        print("-----------------------------")
        for field, count in field_counts.items():
            if count > 1:
                print(f"- {field} is declared {count} times in fields list")

        # Check for any fields that exist in models but not in serializers
        job_fields = self.get_model_fields(Job)
        serializer_fields = self.get_serializer_fields(JobSerializer)
        serializer_field_names = {f["source"] for f in serializer_fields}

        missing_fields = []
        for field in job_fields:
            if field["name"] not in serializer_field_names and field["name"] not in [
                "id"
            ]:
                missing_fields.append(field)

        if missing_fields:
            print("\nMissing Model Fields:")
            print("--------------------")
            for field in missing_fields:
                print(
                    f"- {field['model']}.{field['name']} ({field['type']}) is not handled in serializer"
                )

        # If any issues were found, fail the test
        if (
            isinstance(job_files_field, serializers.DictField)
            or missing_fields
            or any(count > 1 for count in field_counts.values())
        ):
            self.fail("Serializer coverage issues found. See output above.")


class JobApiTests(TestCase):
    fixtures = [
        "company_defaults_test_fixture.json",  # Use test fixture with Demo Company tenant ID
        "logins.json",
        "staff.json",
    ]  # We can't even test without fixtures

    def setUp(self):
        # Run the management command to set up shop jobs
        call_command("create_shop_jobs")
        # Log in with the new test user (corrin+autotest)
        self.client = Client()
        login_successful = self.client.login(
            email="corrin+testing@morrissheetmetal.co.nz",
            password=os.getenv("DB_PASSWORD", "abcde"),
        )
        assert login_successful, "Test user login failed in setUp."

        # Create a job for testing
        self.job = Job.objects.create()

        # Set the job's pricing methodology
        self.job.pricing_methodology = JobPricingMethodology.FIXED_PRICE
        self.job.save()

        # Store references to the job's pricings for testing
        self.estimate_pricing = self.job.latest_estimate_pricing
        self.quote_pricing = self.job.latest_quote_pricing
        self.reality_pricing = self.job.latest_reality_pricing

        # Create related adjustment entries for the estimate pricing
        self.adjustment_entry = AdjustmentEntry.objects.create(
            part=self.estimate_pricing.get_default_part(),
            description="Test adjustment description",
            cost_adjustment=100,
            price_adjustment=150,
        )

        # Create related material and time entries if necessary for testing
        self.material_entry = MaterialEntry.objects.create(
            part=self.quote_pricing.get_default_part(),
            item_code="MAT1",
            description="Material A",
            quantity=3.0,
            unit_cost=30.0,
            unit_revenue=36.0,
        )

        self.time_entry = TimeEntry.objects.create(
            part=self.reality_pricing.get_default_part(),
            description="Time entry description",
            items=2,
            minutes_per_item=60,
            wage_rate=32.0,
            charge_out_rate=105.0,
        )

        self.client = Client()

    def test_job_has_estimate_pricing(self):
        # Test if the job correctly returns the estimate pricing
        self.assertEqual(self.job.latest_estimate_pricing, self.estimate_pricing)

    def test_job_has_quote_pricing(self):
        # Test if the job correctly returns the quote pricing
        self.assertEqual(self.job.latest_quote_pricing, self.quote_pricing)

    def test_job_has_reality_pricing(self):
        # Test if the job correctly returns the reality pricing
        self.assertEqual(self.job.latest_reality_pricing, self.reality_pricing)

    # Removing API endpoint tests as they're testing endpoints that no longer exist
