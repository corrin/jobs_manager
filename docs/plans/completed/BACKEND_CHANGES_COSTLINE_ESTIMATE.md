# Backend Changes Required for CostLine Estimate Creation

## Overview
Update job creation endpoint to automatically create estimate CostLines based on estimated materials and time.

## Files to Modify

1. `/home/corrin/src/jobs_manager/apps/job/serializers/job_serializer.py` - Add fields to JobCreateRequestSerializer
2. `/home/corrin/src/jobs_manager/apps/job/services/job_rest_service.py` - Add CostLine creation logic to create_job()

## Changes Needed

### 1. Update JobCreateRequestSerializer (`apps/job/serializers/job_serializer.py`)

Add two new required fields to `JobCreateRequestSerializer` (around line 384):

```python
class JobCreateRequestSerializer(serializers.Serializer):
    """Serializer for job creation request data."""

    name = serializers.CharField(max_length=255)
    client_id = serializers.UUIDField()
    description = serializers.CharField(required=False, allow_blank=True)
    order_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    contact_id = serializers.UUIDField(required=False, allow_null=True)
    pricing_methodology = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    # NEW FIELDS:
    estimated_materials = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        min_value=0,
        help_text="Estimated material costs in dollars"
    )
    estimated_time = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True,
        min_value=0,
        help_text="Estimated workshop time in hours"
    )
```

### 2. Update JobRestService.create_job() (`apps/job/services/job_rest_service.py`)

Add this logic **inside the existing `with transaction.atomic()` block**, **after** the JobEvent.objects.create() call (around line 112):

```python
import math
from decimal import Decimal

# Inside the transaction.atomic() block, after JobEvent.objects.create():

# Create initial estimate CostLines if provided
estimated_materials = data.get('estimated_materials')
estimated_time = data.get('estimated_time')

if estimated_materials is not None and estimated_time is not None:
    # Get the estimate CostSet (already created by job.save())
    estimate_costset = job.cost_sets.get(kind='estimate')

    # Get company defaults for calculations
    from apps.workflow.models import CompanyDefaults
    company_defaults = CompanyDefaults.objects.first()
    wage_rate = company_defaults.wage_rate
    charge_out_rate = company_defaults.charge_out_rate
    materials_markup = company_defaults.materials_markup

    # Create material cost line
    CostLine.objects.create(
        cost_set=estimate_costset,
        kind='material',
        desc='Estimated materials',
        quantity=Decimal('1.000'),
        unit_cost=estimated_materials,
        unit_rev=estimated_materials * (Decimal('1') + materials_markup)
    )

    # Create workshop time cost line
    CostLine.objects.create(
        cost_set=estimate_costset,
        kind='time',
        desc='Estimated workshop time',
        quantity=estimated_time,
        unit_cost=wage_rate,
        unit_rev=charge_out_rate
    )

    # Calculate office time (1:8 ratio, rounded up to quarter hours)
    office_time_decimal = float(estimated_time) / 8
    office_time_hours = Decimal(str(math.ceil(office_time_decimal * 4) / 4))

    CostLine.objects.create(
        cost_set=estimate_costset,
        kind='time',
        desc='Estimated office time',
        quantity=office_time_hours,
        unit_cost=wage_rate,
        unit_rev=charge_out_rate
    )

    # For fixed_price jobs, copy estimate lines to quote CostSet
    if job.pricing_methodology == 'fixed_price':
        quote_costset = job.cost_sets.get(kind='quote')
        for estimate_line in estimate_costset.cost_lines.all():
            CostLine.objects.create(
                cost_set=quote_costset,
                kind=estimate_line.kind,
                desc=estimate_line.desc,
                quantity=estimate_line.quantity,
                unit_cost=estimate_line.unit_cost,
                unit_rev=estimate_line.unit_rev,
                ext_refs=estimate_line.ext_refs.copy() if estimate_line.ext_refs else {},
                meta=estimate_line.meta.copy() if estimate_line.meta else {}
            )
```

## Implementation Notes

- Material markup is applied to the unit_rev (revenue) field: `unit_rev = unit_cost * (1 + markup)`
- Office time is calculated as 1/8 of workshop time, rounded up to nearest quarter hour
- For fixed_price jobs, estimate CostLines are automatically copied to the quote CostSet
- All fields from estimate_line (including ext_refs and meta) are copied using `.copy()` to avoid shared references
- All logic is inside the existing transaction.atomic() block for data integrity
- Decimal arithmetic is handled properly to avoid float precision issues
- The CostSets are created by `job.save()`, so we query them using `job.cost_sets.get(kind='estimate')`
