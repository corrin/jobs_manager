# Weekend Timesheet Inclusion - Requirements

## Overview

The timesheet system currently excludes weekends from data fetching and processing. This needs to be updated to include Saturday and Sunday in all timesheet operations while maintaining existing functionality.

## Current State Analysis

- ✅ **Fixed**: WeeklyTimesheetService.\_get_week_days() now returns 7 days (Mon-Sun)
- ✅ **Fixed**: Paid leave auto-creation no longer skips weekends
- ✅ **Fixed**: API documentation updated to reflect Mon-Sun coverage
- ❌ **Missing**: Response builders may still slice to 5 days
- ❌ **Missing**: Serializers may expect fixed 5-day structures
- ❌ **Missing**: Frontend may have hardcoded 5-column grids
- ❌ **Missing**: Export services may filter weekends
- ❌ **Missing**: Tests expect 5-day structures

## Requirements

### Functional Requirements

#### 1. Data Processing

- **REQ-001**: All timesheet queries must include weekend dates
- **REQ-002**: Weekly overviews must display 7 days (Mon-Sun)
- **REQ-003**: Daily summaries must work for any day of the week
- **REQ-004**: Leave submissions must allow weekend dates
- **REQ-005**: Time entry creation must accept weekend dates

#### 2. API Endpoints

- **REQ-006**: WeeklyTimesheetAPIView must return 7-day data structures
- **REQ-007**: DailyTimesheetAPIView must handle weekend dates
- **REQ-008**: ModernTimesheetEntryView must accept weekend entries
- **REQ-009**: All date-based queries must include weekends

#### 3. Business Logic

- **REQ-010**: Scheduled hours calculation must work for weekends
- **REQ-011**: Overtime calculations must consider weekend work
- **REQ-012**: Leave processing must include weekends
- **REQ-013**: Status calculations must account for 7-day weeks

#### 4. Data Integrity

- **REQ-014**: No data loss when expanding to 7 days
- **REQ-015**: Backward compatibility maintained
- **REQ-016**: Existing weekend data must be preserved

### Non-Functional Requirements

#### 5. Performance

- **REQ-017**: Query performance must not degrade with weekend inclusion
- **REQ-018**: Response times must remain acceptable
- **REQ-019**: Memory usage must be optimized for 7-day structures

#### 6. Compatibility

- **REQ-020**: IMS export format must remain unchanged (Tue-Fri + next Mon)
- **REQ-021**: Existing API contracts must be maintained
- **REQ-022**: Frontend integration must be seamless

#### 7. Validation

- **REQ-023**: Manual validation must verify weekend functionality
- **REQ-024**: Code review must ensure quality and consistency
- **REQ-025**: Manual testing must cover weekend scenarios

## Constraints and Assumptions

### Technical Constraints

- Database schema supports weekend dates (no constraints)
- JSON field queries work for weekend dates
- CostLine model can store weekend entries
- Existing date parsing handles weekend dates

### Business Constraints

- IMS export format must remain Tue-Fri + next Mon
- Some business rules may discourage weekend work (warnings, not blocks)
- Leave policies may apply to weekends
- Overtime rules may differ for weekends

### Assumptions

- Frontend can be updated to handle 7-column grids
- Users want weekend timesheet capability
- No additional database migrations needed
- Existing weekend data exists and should be preserved

## Feature Flag Implementation

### Mandatory Feature Flag Rules

- **WEEKEND_TIMESHEETS_ENABLED**: Environment variable to control weekend functionality
- **Default Value**: `false` (maintains backward compatibility)
- **Type**: Boolean
- **Scope**: Global application setting

### Feature Flag Behavior

- **When `false` (default)**:

  - Standard mode: Monday-Friday (5 days)
  - IMS mode: Monday-Friday (simplified)
  - Leave processing: Skip weekends
  - All validations remain weekday-only

- **When `true`**:
  - Standard mode: Monday-Sunday (7 days)
  - IMS mode: Monday-Friday (simplified)
  - Leave processing: Include all days
  - Weekend entries allowed

### Implementation Requirements

- **REQ-026**: Feature flag must be checked in all relevant service methods
- **REQ-027**: Feature flag must be configurable via CompanyDefauls model:

```py
from django.core.exceptions import ValidationError
from django.db import models, transaction


class CompanyDefaults(models.Model):
    company_name = models.CharField(max_length=255, primary_key=True)
    is_primary = models.BooleanField(default=True, unique=True)
    time_markup = models.DecimalField(max_digits=5, decimal_places=2, default=0.3)
    materials_markup = models.DecimalField(max_digits=5, decimal_places=2, default=0.2)
    charge_out_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=105.00
    )  # rate per hour
    wage_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=32.00
    )  # rate per hour

    starting_job_number = models.IntegerField(
        default=1,
        help_text="Helper field to set the starting job number based on the latest paper job",
    )
    starting_po_number = models.IntegerField(
        default=1, help_text="Helper field to set the starting purchase order number"
    )
    po_prefix = models.CharField(
        max_length=10,
        default="PO-",
        help_text="Prefix for purchase order numbers (e.g., PO-, JO-)",
    )

    # Google Sheets integration for Job Quotes
    master_quote_template_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL to the master Google Sheets quote template",
    )

    master_quote_template_id = models.CharField(
        null=True,
        blank=True,
        help_text="Google Sheets ID for the quote template",
        max_length=100,
    )

    gdrive_quotes_folder_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL to the Google Drive folder for storing quotes",
    )

    gdrive_quotes_folder_id = models.CharField(
        null=True,
        blank=True,
        help_text="Google Drive folder ID for storing quotes",
        max_length=100,
    )

    # Xero integration
    xero_tenant_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="The Xero tenant ID to use for this company",
    )

    # Default working hours (Mon-Fri, 7am - 3pm)
    mon_start = models.TimeField(default="07:00")
    mon_end = models.TimeField(default="15:00")
    tue_start = models.TimeField(default="07:00")
    tue_end = models.TimeField(default="15:00")
    wed_start = models.TimeField(default="07:00")
    wed_end = models.TimeField(default="15:00")
    thu_start = models.TimeField(default="07:00")
    thu_end = models.TimeField(default="15:00")
    fri_start = models.TimeField(default="07:00")
    fri_end = models.TimeField(default="15:00")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_xero_sync = models.DateTimeField(
        null=True, blank=True, help_text="The last time Xero data was synchronized"
    )
    last_xero_deep_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The last time a deep Xero sync was performed (looking back 90 days)",
    )

    # Shop client configuration
    shop_client_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the internal shop client for tracking shop work (e.g., 'MSM (Shop)')",
    )

    # KPI thresholds
    billable_threshold_green = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=45.0,
        verbose_name="Green Threshold of Billable Hours",
        help_text="Daily billable hours above this threshold are marked in green",
    )
    billable_threshold_amber = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.0,
        verbose_name="Amber Threshold of Billable Hours",
        help_text="Daily billable hours between this threshold and the green threshold are marked in amber",
    )
    daily_gp_target = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1250.0,
        verbose_name="Daily Goal of Gross Profit",
        help_text="Daily gross profit goal in dolars",
    )
    shop_hours_target_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.0,
        verbose_name="Hours percentage goal in Shop Jobs",
        help_text="Target percentage of hours worked in shop jobs",
    )

    class Meta:
        verbose_name = "Company Defaults"
        verbose_name_plural = "Company Defaults"

    def save(self, *args, **kwargs):
        print(
            f"DEBUG: CompanyDefaults.save called with shop_client_name = {self.shop_client_name}"
        )
        if not self.pk and CompanyDefaults.objects.exists():
            raise ValidationError("There can be only one CompanyDefaults instance")
        self.is_primary = True
        print(
            f"DEBUG: About to call super().save() with shop_client_name = {self.shop_client_name}"
        )
        result = super().save(*args, **kwargs)
        print(
            f"DEBUG: After super().save(), shop_client_name = {self.shop_client_name}"
        )
        return result

    @classmethod
    def get_instance(cls) -> "CompanyDefaults":
        """
        Get the singleton instance.
        This is the preferred way to get the CompanyDefaults instance.
        """
        with transaction.atomic():
            return cls.objects.get()

    @property
    def llm_api_key(self):
        """
        Returns the API key of the active LLM provider.
        """
        from .ai_provider import AIProvider

        active_provider = AIProvider.objects.filter(default=True).first()
        return active_provider.api_key if active_provider else None

    def __str__(self):
        return self.company_name

```

- **REQ-028**: Feature flag must support runtime changes without restart
- **REQ-029**: Feature flag must be documented in deployment guides
- **REQ-030**: Feature flag must include migration path for existing data

## Success Criteria

### Functional Success

- [ ] Weekly overviews show 7 days of data
- [ ] Weekend dates can be queried individually
- [ ] Leave can be submitted for weekends
- [ ] Time entries can be created for weekends
- [ ] All calculations work with 7-day data

### Technical Success

- [ ] No breaking changes to existing APIs
- [ ] Performance remains acceptable
- [ ] Feature flag works correctly
- [ ] Manual validation passes

### Business Success

- [ ] Users can track weekend work
- [ ] Reporting includes weekend data
- [ ] Export functionality works correctly
- [ ] Data integrity preserved

## Risk Assessment

### High Risk

- **RISK-001**: Frontend grid components may break with 7 columns
- **RISK-002**: Performance degradation with larger datasets
- **RISK-003**: Feature flag configuration errors

### Medium Risk

- **RISK-004**: Business logic errors in weekend calculations
- **RISK-005**: Export format incompatibilities
- **RISK-006**: Data consistency issues

### Low Risk

- **RISK-007**: API documentation inconsistencies
- **RISK-008**: Minor UI adjustments needed

## Dependencies

### Internal Dependencies

- CostLine model and related queries
- WeeklyTimesheetService functionality
- API endpoint implementations
- Frontend grid components

### External Dependencies

- Database performance with larger result sets
- Frontend framework compatibility
- User acceptance of weekend functionality

## Acceptance Criteria

### Code Quality

- [ ] All code follows existing patterns
- [ ] No hardcoded weekday assumptions
- [ ] Proper error handling for weekend dates
- [ ] Comprehensive logging

### Validation

- [ ] Manual validation of weekend functionality
- [ ] Code review for quality and consistency
- [ ] Manual testing of weekend scenarios
- [ ] Performance monitoring with 7-day data

### Documentation

- [ ] API documentation updated
- [ ] Code comments reflect 7-day functionality
- [ ] User documentation updated if needed

## Out of Scope

### Explicitly Excluded

- Frontend UI redesign (beyond basic 7-column support)
- Database schema changes
- Business rule changes for weekend overtime
- Mobile application updates
- Third-party integration changes

### Future Considerations

- Weekend-specific business rules
- Enhanced reporting for weekend work
- Automated weekend scheduling
- Advanced overtime calculations
