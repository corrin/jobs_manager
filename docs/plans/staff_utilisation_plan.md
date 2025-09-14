# Staff Performance Report Implementation Plan

## Overview

Two APIs to support 1:1 performance management - identify lazy staff, time dumpers, and compare individual performance against team averages.

## API Endpoints

### 1. Team Summary API

**`GET /accounting/api/reports/staff-performance-summary/`**

**Query Parameters:**

- `start_date` (required): Period start date
- `end_date` (required): Period end date

**Response Structure (both APIs use same format):**

```json
{
  "team_averages": {
    "billable_percentage": 75.0,
    "revenue_per_hour": 85.0,
    "profit_per_hour": 45.0,
    "jobs_per_person": 4.2
  },
  "staff": [
    {
      "staff_id": "uuid",
      "name": "John Smith",
      "total_hours": 160.0,
      "billable_hours": 120.0,
      "billable_percentage": 75.0,
      "total_revenue": 12000.0,
      "total_cost": 8000.0,
      "profit": 4000.0,
      "revenue_per_hour": 100.0,
      "profit_per_hour": 50.0,
      "jobs_worked": 5,
      "job_breakdown": [
        {
          "job_id": "uuid",
          "job_number": "J2024-001",
          "job_name": "Custom Brackets",
          "client_name": "ABC Corp",
          "billable_hours": 35.0,
          "non_billable_hours": 5.0,
          "total_hours": 40.0,
          "revenue": 3500.0,
          "cost": 2000.0,
          "profit": 1500.0,
          "revenue_per_hour": 87.5
        }
      ]
    }
  ]
}
```

### 2. Individual Staff API

**`GET /accounting/api/reports/staff-performance/{staff_id}/`**

**Query Parameters:**

- `start_date` (required): Period start date
- `end_date` (required): Period end date

**Response Structure:**
Same as above, but `staff` array contains only one entry with `job_breakdown` populated.

````

## Implementation Components

### 1. Service Layer (`apps/accounting/services.py`)
Add `StaffPerformanceService` class:
- `get_staff_performance_data(start_date, end_date, staff_id=None)` - unified method for both APIs
- Returns team averages + staff array (filtered by staff_id if provided)

### 2. API Views (`apps/accounting/views/staff_performance_views.py`)
- `StaffPerformanceSummaryAPIView` - team summary endpoint
- `StaffPerformanceDetailAPIView` - individual staff endpoint
- Follow error handling patterns with `persist_app_error()`

### 3. Serializers (`apps/accounting/serializers.py`)
- `StaffPerformanceResponseSerializer` - unified response for both APIs
- `StaffPerformanceErrorResponseSerializer` - error handling

### 4. URL Configuration (`apps/accounting/urls.py`)
- `api/reports/staff-performance-summary/`
- `api/reports/staff-performance/<uuid:staff_id>/`

## Data Source & Calculations

### Core Query
Use CostLine with `kind='time'` from actual CostSets:
```python
cost_lines = CostLine.objects.annotate(
    staff_id_meta=RawSQL("JSON_UNQUOTE(JSON_EXTRACT(meta, '$.staff_id'))", ()),
    date_meta=RawSQL("JSON_UNQUOTE(JSON_EXTRACT(meta, '$.date'))", ()),
    is_billable_meta=RawSQL("JSON_UNQUOTE(JSON_EXTRACT(meta, '$.is_billable'))", ()),
).filter(
    cost_set__kind="actual",
    kind="time",
    date_meta__gte=start_date,
    date_meta__lte=end_date
).select_related("cost_set__job__client")
````

### Key Calculations

- **Revenue**: `sum(unit_rev * quantity)` per staff
- **Cost**: `sum(unit_cost * quantity)` per staff
- **Profit**: Revenue - Cost
- **Billable %**: Billable hours / Total hours \* 100
- **Team Averages**: Calculate across all active staff

### Problem Detection Metrics

- **Lazy Staff**: Low billable percentage vs team average
- **Time Dumpers**: High hours per job vs team average
- **Low Performers**: Below average revenue/profit per hour

## Error Handling

- Validate date ranges
- Handle missing staff references gracefully
- Use `persist_app_error()` for exceptions
- Return appropriate HTTP status codes

## Frontend Usage

1. **Main View**: Call summary API, iterate `staff` array for table with team average comparisons
2. **1:1 Drill-down**: Call individual API, access `staff[0]` for detailed job breakdown
3. **Performance Conversations**: "You're 20% below team average on billable hours..."

## API Differences

- **Summary API**: `staff` array has multiple entries, `job_breakdown` omitted for performance
- **Individual API**: `staff` array has one entry, `job_breakdown` populated with detailed job data
