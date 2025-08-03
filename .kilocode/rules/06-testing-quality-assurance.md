# Testing and Quality Assurance

## 🚨 CURRENT TEST STATUS 🚨

### Current Situation

```python
"""
IMPORTANT: We are NOT currently writing unit tests.
This documentation serves as a reference for when we implement tests.

CURRENT PRIORITY:
1. Functionality and delivery
2. Manual testing via frontend
3. Validation in production

FUTURE:
- Implement tests when the codebase stabilizes
- Focus on integration tests first
- Gradually add unit tests
"""
```

## Quality Strategy Without Unit Tests

### Rigorous Manual Validation

```python
# Checklist for manual functionality validation
MANUAL_TESTING_CHECKLIST = {
    'job_creation': [
        'Create job with valid data',
        'Try to create job without name (should fail)',
        'Try to create job without client (should fail)',
        'Check if job appears in the listing',
        'Check if audit was created'
    ],
    'cost_set_operations': [
        'Create estimate CostSet',
        'Add CostLines to CostSet',
        'Check total calculations',
        'Create actual CostSet',
        'Compare estimate vs actual'
    ],
    'xero_integration': [
        'Sync invoice to Xero',
        'Check if data arrived correctly',
        'Test API error scenario',
        'Check error persistence'
    ]
}
```

### Rigorous Code Review

```python
# Checklist for code review
CODE_REVIEW_CHECKLIST = {
    'defensive_programming': [
        'Are all exceptions caught and persisted?',
        'Is input validation present everywhere?',
        'Are database operations using transactions when needed?',
        'No silent fallbacks?'
    ],
    'architecture': [
        'Does code follow Service/Repository pattern?',
        'Is modern CostSet/CostLine architecture used?',
        'No legacy JobPricing models used?',
        'Clear separation between layers?'
    ],
    'error_handling': [
        'Are all errors persisted with persist_app_error()?',
        'Is proper context provided in errors?',
        'Is structured logging present?',
        'Is error severity correct?'
    ]
}
```

## Test Structure (For Future Implementation)

### Test Configuration

```python
# tests/settings.py
from jobs_manager.settings.base import *

# Test-specific settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable unnecessary migrations in tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# In-memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable logging in tests
LOGGING_CONFIG = None

# Email settings for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
```

### Fixtures and Factories

```python
# tests/factories.py
import factory
from django.contrib.auth import get_user_model
from apps.client.models import Client
from apps.job.models import Job, CostSet, CostLine

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    """Factory to create test users."""
    class Meta:
        model = User
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')

class ClientFactory(factory.django.DjangoModelFactory):
    """Factory to create test clients."""
    class Meta:
        model = Client
    name = factory.Faker('company')
    email = factory.LazyAttribute(lambda obj: f"contact@{obj.name.lower().replace(' ', '')}.com")
    status = 'active'

class JobFactory(factory.django.DjangoModelFactory):
    """Factory to create test jobs."""
    class Meta:
        model = Job
    name = factory.Faker('catch_phrase')
    client = factory.SubFactory(ClientFactory)
    created_by = factory.SubFactory(UserFactory)
    status = 'draft'

class CostSetFactory(factory.django.DjangoModelFactory):
    """Factory to create test cost sets."""
    class Meta:
        model = CostSet
    job = factory.SubFactory(JobFactory)
    kind = 'estimate'
    summary = factory.LazyFunction(lambda: {'cost': 1000.0, 'rev': 1200.0, 'hours': 10.0})

class CostLineFactory(factory.django.DjangoModelFactory):
    """Factory to create test cost lines."""
    class Meta:
        model = CostLine
    cost_set = factory.SubFactory(CostSetFactory)
    kind = 'time'
    description = factory.Faker('sentence')
    quantity = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    rate = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    total = factory.LazyAttribute(lambda obj: obj.quantity * obj.rate)
```

### Model Tests

```python
# tests/test_models.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from tests.factories import JobFactory, CostSetFactory, CostLineFactory

class JobModelTest(TestCase):
    """Tests for the Job model."""
    def test_job_creation(self):
        """Test basic job creation."""
        job = JobFactory()
        self.assertIsNotNone(job.id)
        self.assertIsNotNone(job.created_at)
        self.assertIsNotNone(job.updated_at)
        self.assertEqual(job.status, 'draft')
    def test_job_validation(self):
        """Test job validation."""
        job = JobFactory.build(name='')  # Empty name
        with self.assertRaises(ValidationError):
            job.full_clean()
    def test_job_latest_estimate(self):
        """Test latest_estimate property."""
        job = JobFactory()
        # Create multiple cost sets
        old_estimate = CostSetFactory(job=job, kind='estimate')
        new_estimate = CostSetFactory(job=job, kind='estimate')
        self.assertEqual(job.latest_estimate, new_estimate)

class CostLineModelTest(TestCase):
    """Tests for the CostLine model."""
    def test_cost_line_validation(self):
        """Test CostLine validation."""
        cost_line = CostLineFactory.build(
            quantity=Decimal('10.0'),
            rate=Decimal('50.0'),
            total=Decimal('400.0')  # Incorrect total
        )
        with self.assertRaises(ValidationError):
            cost_line.full_clean()
    def test_cost_line_ext_refs_validation(self):
        """Test external references validation."""
        cost_line = CostLineFactory.build(
            kind='time',
            ext_refs={}  # Missing required staff_id
        )
        with self.assertRaises(ValidationError):
            cost_line.full_clean()
```

### Service Tests

```python
# tests/test_services.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from unittest.mock import patch, Mock
from apps.job.services.job_rest_service import JobRestService
from apps.workflow.models.app_error import AppError
from tests.factories import UserFactory, ClientFactory

class JobRestServiceTest(TestCase):
    """Tests for JobRestService."""
    def setUp(self):
        self.user = UserFactory()
        self.client = ClientFactory()
    def test_create_job_success(self):
        """Test successful job creation."""
        job_data = {
            'name': 'Test Job',
            'client_id': str(self.client.id)
        }
        job = JobRestService.create_job(job_data, self.user)
        self.assertEqual(job.name, 'Test Job')
        self.assertEqual(job.client, self.client)
        self.assertEqual(job.created_by, self.user)
    def test_create_job_validation_error(self):
        """Test validation error on job creation."""
        job_data = {
            'name': '',  # Empty name
            'client_id': str(self.client.id)
        }
        with self.assertRaises(ValidationError):
            JobRestService.create_job(job_data, self.user)
        # Check if error was persisted
        self.assertTrue(AppError.objects.filter(
            error_type='ValidationError'
        ).exists())
    def test_create_job_client_not_found(self):
        """Test error when client does not exist."""
        job_data = {
            'name': 'Test Job',
            'client_id': 'non-existent-id'
        }
        with self.assertRaises(ValidationError):
            JobRestService.create_job(job_data, self.user)
    @patch('apps.job.services.job_rest_service.external_api_call')
    def test_external_api_error_handling(self, mock_api):
        """Test external API error handling."""
        mock_api.side_effect = Exception("API Error")
        with self.assertRaises(Exception):
            JobRestService.sync_with_external_system('job-id')
        # Check if error was persisted
        self.assertTrue(AppError.objects.filter(
            error_message__contains='API Error'
        ).exists())
```

### API Tests

```python
# tests/test_api.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from tests.factories import UserFactory, JobFactory, ClientFactory

class JobAPITest(TestCase):
    """Tests for the Jobs API."""
    def setUp(self):
        self.client_api = APIClient()
        self.user = UserFactory()
        self.client_api.force_authenticate(user=self.user)
    def test_list_jobs(self):
        """Test job listing."""
        JobFactory.create_batch(3)
        url = reverse('job-list')
        response = self.client_api.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
    def test_create_job(self):
        """Test job creation via API."""
        client = ClientFactory()
        data = {
            'name': 'New Job',
            'client_id': str(client.id)
        }
        url = reverse('job-list')
        response = self.client_api.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Job')
    def test_create_job_validation_error(self):
        """Test validation error in API."""
        data = {
            'name': '',  # Empty name
            'client_id': 'invalid-id'
        }
        url = reverse('job-list')
        response = self.client_api.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
    def test_unauthorized_access(self):
        """Test unauthorized access."""
        self.client_api.force_authenticate(user=None)
        url = reverse('job-list')
        response = self.client_api.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

### Integration Tests

```python
# tests/test_integration.py
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from unittest.mock import patch
from apps.job.services.costing_service import CostingService
from apps.workflow.models.app_error import AppError
from tests.factories import JobFactory

class CostingIntegrationTest(TransactionTestCase):
    """Integration tests for costing system."""
    def test_create_cost_set_with_transaction_rollback(self):
        """Test transaction rollback on error."""
        job = JobFactory()
        cost_data = {
            'kind': 'estimate',
            'lines': [
                {
                    'kind': 'time',
                    'description': 'Development',
                    'quantity': 10,
                    'rate': 50,
                    'ext_refs': {'staff_id': 'invalid-id'}  # Will cause error
                }
            ]
        }
        with self.assertRaises(Exception):
            CostingService.create_cost_set_with_lines(job, cost_data)
        # Check that no CostSet was created
        self.assertEqual(job.cost_sets.count(), 0)
        # Check that error was persisted
        self.assertTrue(AppError.objects.exists())
    @patch('apps.xero.services.xero_api.sync_invoice')
    def test_xero_integration_error_handling(self, mock_sync):
        """Test error handling in Xero integration."""
        mock_sync.side_effect = Exception("Xero API Error")
        job = JobFactory()
        with self.assertRaises(Exception):
            # Simulate operation that uses Xero
            pass
        # Check error persistence
        self.assertTrue(AppError.objects.filter(
            error_message__contains='Xero API Error'
        ).exists())
```

## Code Quality Tools

### Black Configuration (Formatting)

```python
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py39']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
  | migrations
)/
'''
```

### Flake8 Configuration (Linting)

```ini
# setup.cfg
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude =
    .git,
    __pycache__,
    migrations,
    .venv,
    build,
    dist
per-file-ignores =
    __init__.py:F401
```

### isort Configuration (Imports)

```python
# pyproject.toml
[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_django = "django"
known_first_party = "apps"
sections = ["FUTURE", "STDLIB", "DJANGO", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]
```

## Quality Metrics

### Code Coverage (Future)

```python
# .coveragerc
[run]
source = apps
omit =
    */migrations/*
    */tests/*
    */venv/*
    manage.py
    */settings/*
    */wsgi.py
    */asgi.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

## Related References

- See: [01-architecture-design-patterns.md](./01-architecture-design-patterns.md)
- See: [05-error-management-logging.md](./05-error-management-logging.md)
- See: [07-security-performance.md](./07-security-performance.md)
