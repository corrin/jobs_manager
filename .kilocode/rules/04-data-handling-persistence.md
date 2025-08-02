# Data Handling and Persistence

## Database Architecture

### 🚨 MANDATORY MODERN ARCHITECTURE 🚨

**For ALL new development, ONLY use:**

```python
# Modern CostSet/CostLine architecture
Job → CostSet (1:many) → CostLine (1:many)
CostLine → external references via ext_refs JSON field
PurchaseOrder → PurchaseOrderLine → Stock → CostLine (via ext_refs)
Staff → CostLine (time entries via ext_refs)
```

**STRICTLY FORBIDDEN in new code:**

```python
# Legacy models - DO NOT USE
Job → JobPricing (1:many) → TimeEntry/MaterialEntry/AdjustmentEntry (1:many)
Staff → TimeEntry (1:many)
PurchaseOrder → PurchaseOrderLine → Stock → MaterialEntry
```

### Model Design Patterns

```python
import uuid
from django.db import models
from simple_history.models import HistoricalRecords

class BaseModel(models.Model):
    """Base model with required standards."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Job(BaseModel):
    """Job model with mandatory auditing."""
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    client = models.ForeignKey('client.Client', on_delete=models.PROTECT)
    # SimpleHistory for auditing - MANDATORY on critical models
    history = HistoricalRecords()
    class Meta:
        db_table = "job_job"  # Format app_model
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["client", "status"]),
        ]
    def save(self, *args, **kwargs):
        """Override save with mandatory validation."""
        self.full_clean()  # Validate before saving
        super().save(*args, **kwargs)
```

### UUID Primary Keys

```python
# ALWAYS use UUID for primary keys
class CostSet(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey('job.Job', on_delete=models.CASCADE, related_name='cost_sets')
    kind = models.CharField(max_length=20, choices=COST_SET_KINDS)
    # Flexible external references via JSON
    ext_refs = models.JSONField(default=dict, blank=True)
    summary = models.JSONField(default=dict, blank=True)
```

## Migration Strategies

### Safe Data Migrations

```python
# migrations/0001_migrate_to_costset.py
from django.db import migrations
from django.db.models import Q

def migrate_job_pricing_to_cost_set(apps, schema_editor):
    """Migrate legacy JobPricing to modern CostSet."""
    Job = apps.get_model('job', 'Job')
    JobPricing = apps.get_model('job', 'JobPricing')  # Legacy model
    CostSet = apps.get_model('job', 'CostSet')
    CostLine = apps.get_model('job', 'CostLine')
    for job in Job.objects.all():
        # Migrate each JobPricing to CostSet
        for pricing in job.pricings.all():
            cost_set = CostSet.objects.create(
                job=job,
                kind='estimate' if pricing.is_estimate else 'actual',
                summary={
                    'cost': float(pricing.total_cost or 0),
                    'rev': float(pricing.total_revenue or 0),
                    'hours': float(pricing.total_hours or 0),
                }
            )
            # Migrate TimeEntries to CostLines
            for time_entry in pricing.time_entries.all():
                CostLine.objects.create(
                    cost_set=cost_set,
                    kind='time',
                    description=time_entry.description,
                    quantity=time_entry.hours,
                    rate=time_entry.rate,
                    total=time_entry.hours * time_entry.rate,
                    ext_refs={
                        'staff_id': str(time_entry.staff.id),
                        'date': time_entry.date.isoformat(),
                        'legacy_time_entry_id': str(time_entry.id)
                    }
                )
class Migration(migrations.Migration):
    dependencies = [
        ('job', '0001_create_costset_models'),
    ]
    operations = [
        migrations.RunPython(
            migrate_job_pricing_to_cost_set,
            reverse_code=migrations.RunPython.noop
        ),
    ]
```

### Rollback Strategies

```python
# Always include rollback code when possible
def reverse_migration(apps, schema_editor):
    """Rollback migration if needed."""
    CostSet = apps.get_model('job', 'CostSet')
    JobPricing = apps.get_model('job', 'JobPricing')
    # Only rollback if legacy data still exists
    for cost_set in CostSet.objects.all():
        if not JobPricing.objects.filter(
            job=cost_set.job,
            kind=cost_set.kind
        ).exists():
            # Recreate JobPricing if it doesn't exist
            JobPricing.objects.create(
                job=cost_set.job,
                total_cost=cost_set.summary.get('cost', 0),
                # ... other fields
            )
```

## ORM Patterns and Query Optimization

### QuerySet Optimization

```python
class JobQuerySet(models.QuerySet):
    """Custom QuerySet with optimizations."""
    def with_client_and_costs(self):
        """Optimize queries with select_related and prefetch_related."""
        return self.select_related('client').prefetch_related(
            'cost_sets__cost_lines',
            'people',
            'events'
        )
    def active_jobs(self):
        """Filter only active jobs."""
        return self.filter(
            status__in=['awaiting_approval', 'approved', 'in_progress']
        )
    def with_cost_summary(self):
        """Annotate with cost summary."""
        from django.db.models import Sum, Case, When, DecimalField
        return self.annotate(
            total_estimated_cost=Sum(
                Case(
                    When(cost_sets__kind='estimate', then='cost_sets__summary__cost'),
                    default=0,
                    output_field=DecimalField()
                )
            ),
            total_actual_cost=Sum(
                Case(
                    When(cost_sets__kind='actual', then='cost_sets__summary__cost'),
                    default=0,
                    output_field=DecimalField()
                )
            )
        )
class Job(BaseModel):
    objects = JobQuerySet.as_manager()
    @property
    def latest_estimate(self):
        """Get latest estimate CostSet."""
        return self.cost_sets.filter(kind='estimate').order_by('-created_at').first()
    @property
    def latest_actual(self):
        """Get latest actual CostSet."""
        return self.cost_sets.filter(kind='actual').order_by('-created_at').first()
```

## Data Validation

### Model Validation

```python
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal

class CostLine(BaseModel):
    """Cost line with strict validation."""
    cost_set = models.ForeignKey('CostSet', on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=COST_LINE_KINDS)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    total = models.DecimalField(max_digits=12, decimal_places=2)
    def clean(self):
        """Custom validation."""
        super().clean()
        # Validate total calculation
        expected_total = self.quantity * self.rate
        if abs(self.total - expected_total) > Decimal('0.01'):
            raise ValidationError({
                'total': f'Total must be {expected_total} (quantity × rate)'
            })
        # Validate external references by type
        if self.kind == 'time' and not self.ext_refs.get('staff_id'):
            raise ValidationError({
                'ext_refs': 'staff_id required for time entries'
            })
        if self.kind == 'material' and not self.ext_refs.get('stock_id'):
            raise ValidationError({
                'ext_refs': 'stock_id required for material entries'
            })
    def save(self, *args, **kwargs):
        """Override save with validation."""
        self.full_clean()
        super().save(*args, **kwargs)
        # Update parent CostSet summary
        self.cost_set.update_summary()
```

### Business Rule Validation

```python
class JobBusinessRules:
    """Business rules for Job validation."""
    @staticmethod
    def validate_status_transition(job: Job, new_status: str) -> None:
        """Validate status transition."""
        valid_transitions = {
            'draft': ['awaiting_approval'],
            'awaiting_approval': ['approved', 'draft', 'rejected'],
            'approved': ['in_progress', 'on_hold'],
            'in_progress': ['completed', 'on_hold', 'approved'],
            'on_hold': ['in_progress', 'approved'],
            'completed': ['archived'],
            'archived': [],  # Cannot leave archived
            'rejected': ['draft']
        }
        if new_status not in valid_transitions.get(job.status, []):
            raise ValidationError(
                f'Cannot change status from {job.status} to {new_status}'
            )
    @staticmethod
    def validate_can_delete(job: Job) -> None:
        """Validate if job can be deleted."""
        # Cannot delete if has actual costs
        actual_cost_set = job.latest_actual
        if actual_cost_set and (
            actual_cost_set.summary.get('cost', 0) > 0 or
            actual_cost_set.summary.get('rev', 0) > 0
        ):
            raise ValidationError(
                'Cannot delete job with actual costs or revenue'
            )
        # Cannot delete if in progress
        if job.status in ['in_progress', 'completed', 'archived']:
            raise ValidationError(
                f'Cannot delete job with status {job.status}'
            )
```

## Transaction Management

### Transaction Patterns

```python
from django.db import transaction
from django.db.models import F

class CostingService:
    """Service for costing operations with transactions."""
    @staticmethod
    @transaction.atomic
    def create_cost_set_with_lines(job: Job, cost_data: dict) -> CostSet:
        """Create CostSet with CostLines in an atomic transaction."""
        # Create CostSet
        cost_set = CostSet.objects.create(
            job=job,
            kind=cost_data['kind'],
            summary={'cost': 0, 'rev': 0, 'hours': 0}
        )
        total_cost = Decimal('0')
        total_hours = Decimal('0')
        # Create CostLines
        for line_data in cost_data.get('lines', []):
            cost_line = CostLine.objects.create(
                cost_set=cost_set,
                kind=line_data['kind'],
                description=line_data['description'],
                quantity=line_data['quantity'],
                rate=line_data['rate'],
                total=line_data['quantity'] * line_data['rate'],
                ext_refs=line_data.get('ext_refs', {})
            )
            total_cost += cost_line.total
            if cost_line.kind == 'time':
                total_hours += cost_line.quantity
        # Update summary
        cost_set.summary = {
            'cost': float(total_cost),
            'rev': float(total_cost * Decimal('1.2')),  # Example markup
            'hours': float(total_hours)
        }
        cost_set.save()
        return cost_set
    @staticmethod
    @transaction.atomic
    def update_stock_and_create_cost_line(
        cost_set: CostSet,
        stock_item: 'Stock',
        quantity_used: Decimal
    ) -> CostLine:
        """Update stock and create cost line atomically."""
        # Check available stock
        if stock_item.quantity_available < quantity_used:
            raise ValidationError('Insufficient stock')
        # Update stock using F() to avoid race conditions
        Stock.objects.filter(id=stock_item.id).update(
            quantity_used=F('quantity_used') + quantity_used
        )
        # Reload to get updated values
        stock_item.refresh_from_db()
        # Create cost line
        cost_line = CostLine.objects.create(
            cost_set=cost_set,
            kind='material',
            description=f'Material: {stock_item.description}',
            quantity=quantity_used,
            rate=stock_item.unit_cost,
            total=quantity_used * stock_item.unit_cost,
            ext_refs={'stock_id': str(stock_item.id)}
        )
        return cost_line
```

### Savepoints for Complex Operations

```python
from django.db import transaction

@transaction.atomic
def complex_job_operation(job_id: UUID, operation_data: dict):
    """Complex operation with savepoints."""
    job = Job.objects.get(id=job_id)
    # Savepoint before risky operations
    sid = transaction.savepoint()
    try:
        # Operation 1: Update job
        job.status = operation_data['new_status']
        job.save()
        # Operation 2: Create cost set
        cost_set = CostSet.objects.create(
            job=job,
            kind=operation_data['cost_kind']
        )
        # Operation 3: Process cost lines
        for line_data in operation_data.get('cost_lines', []):
            # Operation that may fail
            process_cost_line(cost_set, line_data)
        # If here, commit savepoint
        transaction.savepoint_commit(sid)
    except Exception as e:
        # Rollback to savepoint
        transaction.savepoint_rollback(sid)
        # Persist error and re-raise
        from apps.workflow.services.error_persistence import persist_app_error
        persist_app_error(e)
        raise
```

## Caching Strategies

### Model Cache

```python
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

class Job(BaseModel):
    """Job with integrated cache."""
    def get_cost_summary(self, use_cache=True):
        """Get cost summary with cache."""
        cache_key = f'job_cost_summary_{self.id}'
        if use_cache:
            cached_summary = cache.get(cache_key)
            if cached_summary is not None:
                return cached_summary
        # Calculate summary
        summary = {
            'estimated_cost': self.latest_estimate.summary.get('cost', 0) if self.latest_estimate else 0,
            'actual_cost': self.latest_actual.summary.get('cost', 0) if self.latest_actual else 0,
            'profit_margin': 0  # Calculate...
        }
        # Cache for 1 hour
        cache.set(cache_key, summary, 3600)
        return summary
    def invalidate_cache(self):
        """Invalidate cache related to the job."""
        cache_keys = [
            f'job_cost_summary_{self.id}',
            f'job_details_{self.id}',
            f'client_jobs_{self.client_id}'
        ]
        cache.delete_many(cache_keys)
    def save(self, *args, **kwargs):
        """Override save with cache invalidation."""
        super().save(*args, **kwargs)
        self.invalidate_cache()
```

## Related References

- See: [01-architecture-design-patterns.md](./01-architecture-design-patterns.md)
- See: [02-code-organization-structure.md](./02-code-organization-structure.md)
- See: [06-error-management-logging.md](./06-error-management-logging.md)
- See: [08-security-performance.md](./08-security-performance.md)
