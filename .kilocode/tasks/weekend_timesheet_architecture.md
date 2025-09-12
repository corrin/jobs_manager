# Weekend Timesheet Inclusion - Architecture Overview

## System Architecture

### Current Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Layer      │    │  Service Layer  │
│   (Vue.js)      │◄──►│   (Django REST)  │◄──►│   (Business     │
│                 │    │                  │    │    Logic)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Database      │    │   Serializers    │    │   Models        │
│   (MariaDB)     │    │   (DRF)          │    │   (Django)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Weekend Inclusion Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Layer      │    │  Service Layer  │
│   (7-day grid)  │◄──►│   (7-day data)   │◄──►│   (7-day logic) │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Database      │    │   Serializers    │    │   Models        │
│   (Weekend OK)  │    │   (7-day compat) │    │   (UUID dates)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Component Analysis

### 1. Service Layer (`WeeklyTimesheetService`)

#### Current Implementation
```python
class WeeklyTimesheetService:
    @classmethod
    def _get_week_days(cls, start_date, export_to_ims=False):
        if export_to_ims:
            return cls._get_ims_week(start_date)  # Tue-Fri + next Mon
        else:
            return [start_date + timedelta(days=i) for i in range(5)]  # Mon-Fri
```

#### Updated Implementation
```python
class WeeklyTimesheetService:
    @classmethod
    def _get_week_days(cls, start_date, export_to_ims=False):
        if export_to_ims:
            return cls._get_ims_week(start_date)  # Mon-Fri (simplified)
        else:
            return [start_date + timedelta(days=i) for i in range(7)]  # Mon-Sun
```

#### Key Changes
- **Standard mode**: Returns 7 days instead of 5
- **IMS mode**: Changed to Monday-Friday (simplified from Tue-Fri + next Mon)
- **Leave processing**: Removed weekend skip logic

### 2. API Layer (`TimesheetResponseMixin`)

#### Current Flow
```
Request → build_timesheet_response() → WeeklyTimesheetService.get_weekly_overview()
    ↓
Service returns 5-day data → Serializer → Response
```

#### Updated Flow
```
Request → build_timesheet_response() → WeeklyTimesheetService.get_weekly_overview()
    ↓
Service returns 7-day data → Serializer → Response
```

#### Key Changes
- No changes needed - automatically handles 7-day data from service
- Serializers must support variable-length day arrays
- Response structure remains compatible

### 3. View Layer (`ModernTimesheetEntryView`, `ModernTimesheetDayView`)

#### Current Implementation
```python
# Individual entries - already weekend-compatible
def get(self, request):
    # Accepts any date parameter
    entry_date = request.query_params.get("date")
    # No weekday validation

def post(self, request):
    # Creates entries for any date
    entry_date = validated_data["date"]
    # No weekend restrictions
```

#### Key Changes
- **No changes required** - views already accept any date
- **Validation**: Ensure no hidden weekday checks
- **Queries**: Confirm date filtering works for weekends

### 4. Data Layer (CostLine Model)

#### Current Schema
```python
class CostLine(models.Model):
    meta = models.JSONField()  # Contains date, staff_id, etc.
    # Date stored as: {"date": "2024-01-13", ...}
```

#### Weekend Compatibility
- ✅ **Database**: No constraints on weekend dates
- ✅ **JSON queries**: MariaDB JSON_EXTRACT works with any date
- ✅ **Storage**: Weekend dates store normally
- ✅ **Retrieval**: Queries work for any date

## Data Flow Architecture

### Standard Weekly Overview (7 days)
```
1. API Request: GET /api/weekly/?start_date=2024-01-15
2. TimesheetResponseMixin.build_timesheet_response()
3. WeeklyTimesheetService.get_weekly_overview(start_date)
4. _get_week_days() → [Mon, Tue, Wed, Thu, Fri, Sat, Sun]
5. _get_staff_data(week_days) → Process all 7 days
6. Return 7-day data structure
7. Serializer formats response
8. Frontend receives 7 columns
```

### IMS Export (Special format)
```
1. API Request: GET /api/weekly/ims/?start_date=2024-01-15
2. TimesheetResponseMixin.build_timesheet_response(export_to_ims=True)
3. WeeklyTimesheetService.get_weekly_overview(start_date, export_to_ims=True)
4. _get_ims_week() → [Mon, Tue, Wed, Thu, Fri]
5. _get_staff_data(week_days, export_to_ims=True) → IMS processing
6. Return IMS-formatted data
7. Serializer formats IMS response
8. Export uses Monday-Friday format (simplified)
```

### Individual Day Entry
```
1. API Request: POST /api/entries/ with weekend date
2. ModernTimesheetEntryView.post()
3. Validate date (no weekend restrictions)
4. Create CostLine with weekend date in meta
5. Return success response
```

## Integration Points

### Frontend Integration
```
┌─────────────────────────────────────────────────────────────┐
│ Frontend Grid Component                                    │
├─────────────────────────────────────────────────────────────┤
│ Headers: [Mon, Tue, Wed, Thu, Fri, Sat, Sun]              │
│ Data:   [data, data, data, data, data, data, data]         │
│ Totals:  [sum, sum, sum, sum, sum, sum, sum]               │
└─────────────────────────────────────────────────────────────┘
```

### Database Integration
```
CostLine.meta JSON structure:
{
  "staff_id": "uuid",
  "date": "2024-01-13",  // Weekend dates OK
  "is_billable": true,
  "wage_rate": 25.0,
  "created_from_timesheet": true
}
```

### Export Integration
```
IMS Export: Monday-Friday (simplified)
Standard Export: Mon-Sun (new capability)
Xero Integration: Includes weekend dates
```

## Validation Architecture

### Input Validation
```python
# Before: Weekend blocking
if date.weekday() >= 5:
    raise ValidationError("Weekends not allowed")

# After: Weekend allowed
# No weekday validation
```

### Business Rule Validation
```python
# Weekend warnings (optional)
if date.weekday() >= 5:
    logger.warning(f"Weekend work on {date}")

# But allow the entry
```

## Performance Considerations

### Query Optimization
- **JSON field queries**: Use database indexes on JSON fields
- **Date range queries**: Ensure proper indexing on date fields
- **Batch processing**: Handle 7-day data efficiently

### Memory Management
- **Response size**: 7-day data is ~40% larger than 5-day
- **Caching**: Update cache keys to include weekend data
- **Pagination**: Consider pagination for large datasets

## Testing Architecture

### Unit Tests
```python
def test_weekly_overview_includes_weekends(self):
    # Test 7-day data structure
    overview = WeeklyTimesheetService.get_weekly_overview(start_date)
    self.assertEqual(len(overview['week_days']), 7)
    self.assertEqual(len(overview['staff_data'][0]['weekly_hours']), 7)
```

### Integration Tests
```python
def test_end_to_end_weekend_entry(self):
    # Create weekend entry
    response = self.client.post('/api/entries/', weekend_data)
    self.assertEqual(response.status_code, 201)

    # Verify in weekly overview
    overview = self.client.get('/api/weekly/')
    weekend_data = overview.data['staff_data'][0]['weekly_hours'][5]  # Saturday
    self.assertIsNotNone(weekend_data['hours'])
```

## Deployment Strategy

### Phased Rollout
1. **Phase 1**: Backend changes (service layer)
2. **Phase 2**: API updates (response builders)
3. **Phase 3**: Frontend updates (7-column grids)
4. **Phase 4**: Testing and validation

### Feature Flags
```python
# Mandatory: Feature flag for weekend functionality
WEEKEND_TIMESHEETS_ENABLED = os.getenv('WEEKEND_TIMESHEETS_ENABLED', 'false')

if WEEKEND_TIMESHEETS_ENABLED == 'true':
    # Weekend mode enabled
    week_days = [start_date + timedelta(days=i) for i in range(7)]  # Mon-Sun
    ims_week = [start_date + timedelta(days=i) for i in range(5)]   # Mon-Fri
    skip_weekends = False
else:
    # Legacy mode (default)
    week_days = [start_date + timedelta(days=i) for i in range(5)]  # Mon-Fri
    ims_week = cls._get_ims_week_legacy(start_date)                # Tue-Fri + next Mon
    skip_weekends = True
```

### Feature Flag Integration
```python
class WeeklyTimesheetService:
    @classmethod
    def _get_week_days(cls, start_date, export_to_ims=False):
        """Get list of days for the week based on feature flag."""
        weekend_enabled = os.getenv('WEEKEND_TIMESHEETS_ENABLED', 'false') == 'true'

        if export_to_ims:
            if weekend_enabled:
                return cls._get_ims_week_simple(start_date)  # Mon-Fri
            else:
                return cls._get_ims_week_legacy(start_date)  # Tue-Fri + next Mon
        else:
            if weekend_enabled:
                return [start_date + timedelta(days=i) for i in range(7)]  # Mon-Sun
            else:
                return [start_date + timedelta(days=i) for i in range(5)]  # Mon-Fri
```

## Monitoring and Observability

### Key Metrics
- **Response times**: Monitor API performance with 7-day data
- **Error rates**: Track weekend-specific errors
- **Data completeness**: Ensure weekend entries are processed
- **User adoption**: Track weekend entry creation

### Logging
```python
logger.info(f"Processing {len(week_days)}-day timesheet for {start_date}")
logger.info(f"Weekend entries found: {weekend_count}")
```

## Security Considerations

### Data Access
- **Authorization**: Same permissions apply to weekend data
- **Audit trails**: Weekend entries logged normally
- **Data integrity**: Weekend dates validated like weekdays

### Input Validation
- **Date format**: Weekend dates use same validation
- **Business rules**: Weekend entries subject to same rules
- **Rate limiting**: Same limits apply

## Future Extensions

### Weekend-Specific Features
- **Weekend rates**: Different rates for weekend work
- **Overtime rules**: Weekend overtime calculations
- **Scheduling**: Weekend shift planning
- **Reporting**: Weekend-specific analytics

### Advanced Analytics
- **Weekend patterns**: Analyze weekend work trends
- **Productivity metrics**: Compare weekday vs weekend productivity
- **Cost analysis**: Weekend labor cost tracking

This architecture ensures seamless weekend inclusion while maintaining backward compatibility and system performance.
