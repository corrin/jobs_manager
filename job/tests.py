import json
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

from job.models import Job, JobPricing, Part
from job.models.material_entry import MaterialEntry
from job.models.adjustment_entry import AdjustmentEntry
from timesheet.models import TimeEntry
from job.serializers.job_pricing_serializer import JobPricingSerializer
from job.helpers import DecimalEncoder
from accounts.models import Staff

User = get_user_model()


class JobPricingSerializationTest(TestCase):
    """Test that JobPricing serialization handles UUIDs correctly."""
    fixtures = ['workflow/fixtures/initial_data.json']
    
    def setUp(self):
        """Set up test data."""
        # Create a staff member
        self.staff = Staff.objects.create(
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        # Create a job
        self.job = Job.objects.create(
            name='Test Job',
            job_number=1001,
            pricing_methodology='time_materials'  # Explicitly set the field that's missing from DB
        )
        
        # Create a job pricing
        self.job_pricing = JobPricing.objects.create(
            job=self.job,
            pricing_type='estimate'
        )
        
        # Create a part
        self.part = Part.objects.create(
            job_pricing=self.job_pricing,
            name='Test Part',
            description='Test part description'
        )
        
        # Create entries with various data types
        self.time_entry = TimeEntry.objects.create(
            part=self.part,
            staff=self.staff,
            description='Test time entry',
            wage_rate=Decimal('25.00'),
            charge_out_rate=Decimal('50.00'),
            hours=Decimal('2.5'),
            is_billable=True
        )
        
        self.material_entry = MaterialEntry.objects.create(
            part=self.part,
            description='Test material',
            quantity=Decimal('10.0'),
            unit_cost=Decimal('5.50'),
            unit_revenue=Decimal('8.25')
        )
        
        self.adjustment_entry = AdjustmentEntry.objects.create(
            part=self.part,
            description='Test adjustment',
            cost_adjustment=Decimal('100.00'),
            price_adjustment=Decimal('150.00')
        )
    
    def test_job_pricing_serialization_no_uuids(self):
        """Test that JobPricingSerializer doesn't leak UUID objects to JSON encoder."""
        # Serialize the job pricing
        serializer = JobPricingSerializer(self.job_pricing)
        serialized_data = serializer.data
        
        # Try to convert to JSON using DecimalEncoder
        # This should not raise any UUID-related errors
        try:
            json_string = json.dumps(serialized_data, cls=DecimalEncoder)
            # If we get here, no UUIDs leaked through
            self.assertIsInstance(json_string, str)
            
            # Parse it back to verify it's valid JSON
            parsed_data = json.loads(json_string)
            self.assertIsInstance(parsed_data, dict)
            
            # Verify that all ID fields are strings, not UUIDs
            self.assertIsInstance(parsed_data['id'], str)
            
            # Check parts
            self.assertIn('parts', parsed_data)
            for part in parsed_data['parts']:
                self.assertIsInstance(part['id'], str)
                
                # Check time entries
                for time_entry in part.get('time_entries', []):
                    self.assertIsInstance(time_entry['id'], str)
                    if 'part' in time_entry:
                        self.assertIsInstance(time_entry['part'], str)
                
                # Check material entries
                for material_entry in part.get('material_entries', []):
                    self.assertIsInstance(material_entry['id'], str)
                    if 'part' in material_entry:
                        self.assertIsInstance(material_entry['part'], str)
                
                # Check adjustment entries
                for adjustment_entry in part.get('adjustment_entries', []):
                    self.assertIsInstance(adjustment_entry['id'], str)
                    if 'part' in adjustment_entry:
                        self.assertIsInstance(adjustment_entry['part'], str)
                        
        except TypeError as e:
            if 'UUID' in str(e):
                self.fail(f"UUID objects leaked to JSON encoder: {e}")
            else:
                raise
    
    def test_decimal_encoder_handles_uuids_gracefully(self):
        """Test that DecimalEncoder handles UUIDs gracefully if they do appear."""
        test_uuid = uuid.uuid4()
        test_data = {
            'decimal_field': Decimal('123.45'),
            'uuid_field': test_uuid,
            'normal_field': 'test'
        }
        
        # This should not raise an exception, but should log an error
        json_string = json.dumps(test_data, cls=DecimalEncoder)
        parsed_data = json.loads(json_string)
        
        # UUID should be converted to string
        self.assertEqual(parsed_data['uuid_field'], str(test_uuid))
        self.assertEqual(parsed_data['decimal_field'], 123.45)
        self.assertEqual(parsed_data['normal_field'], 'test')
