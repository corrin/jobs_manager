# Staff Date-Based Filtering Implementation Plan

## Problem Statement

The current staff filtering system uses an inconsistent boolean `is_active` field. We need to implement date-based staff filtering that can answer "who was employed on date X" while avoiding field duplication and maintaining data integrity.

## Current State Analysis

### Staff Model Fields

- `date_joined` - When staff record was created in Django (close enough to employment start)
- `is_active` - Boolean active/inactive flag (creates potential for inconsistency)
- No employment end date tracking

### Current API Issues

- **`/timesheet/api/staff/`**: Missing `is_active` filter entirely, uses only `get_excluded_staff()`
- **`/accounts/api/staff/all/`**: Uses `Staff.objects.all()` by default, optional exclusions
- **Inconsistent filtering**: Different endpoints use different filtering rules
- **No date-based logic**: Cannot determine who was employed on a specific historical date

## Solution: Replace is_active with date_left

### Phase 1: Database Changes

#### Migration 1: Add date_left field

```python
# 0006_add_date_left_field.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_alter_staff_groups_alter_staff_user_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='date_left',
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Date staff member left employment"
            ),
        ),
    ]
```

#### Migration 2: Data migration

```python
# 0007_migrate_is_active_to_date_left.py
from django.db import migrations
from django.utils import timezone

def migrate_inactive_staff(apps, schema_editor):
    Staff = apps.get_model('accounts', 'Staff')
    today = timezone.now().date()

    # Set date_left to today for all currently inactive staff
    Staff.objects.filter(is_active=False).update(date_left=today)

def reverse_migration(apps, schema_editor):
    Staff = apps.get_model('accounts', 'Staff')

    # Set is_active=False for staff with date_left
    Staff.objects.filter(date_left__isnull=False).update(is_active=False)

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0006_add_date_left_field'),
    ]

    operations = [
        migrations.RunPython(migrate_inactive_staff, reverse_migration),
    ]
```

#### Migration 3: Remove is_active field

```python
# 0008_remove_is_active_field.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0007_migrate_is_active_to_date_left'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='staff',
            name='is_active',
        ),
    ]
```

### Phase 2: Model Updates

#### Staff Model Changes

```python
# apps/accounts/models.py
class Staff(AbstractBaseUser, PermissionsMixin):
    # ... existing fields ...

    # Remove: is_active = models.BooleanField(default=True)
    # Add:
    date_left = models.DateField(
        null=True,
        blank=True,
        help_text="Date staff member left employment"
    )

    # ... rest of model ...

    @property
    def is_currently_active(self) -> bool:
        """Check if staff member is currently active"""
        return self.date_left is None or self.date_left > timezone.now().date()
```

#### StaffManager Updates

```python
# apps/accounts/managers.py
class StaffManager(BaseManagerClass):
    # ... existing methods ...

    def active_on_date(self, target_date: date) -> QuerySet["Staff"]:
        """Get staff members who were employed on a specific date."""
        return self.filter(
            date_joined__date__lte=target_date
        ).filter(
            models.Q(date_left__isnull=True) | models.Q(date_left__gt=target_date)
        )

    def currently_active(self) -> QuerySet["Staff"]:
        """Get currently active staff (replaces is_active=True filters)"""
        from django.utils import timezone
        return self.active_on_date(timezone.now().date())
```

### Phase 3: Code Updates

#### Replace All is_active References

Search and replace throughout codebase:

- `Staff.objects.filter(is_active=True)` → `Staff.objects.currently_active()`
- `staff.is_active` → `staff.is_currently_active`
- Forms, services, views, serializers, utilities

#### API Updates

**Timesheet Staff API** (`apps/timesheet/views/api.py`):

```python
class StaffListAPIView(APIView):
    def get(self, request):
        # Add required date parameter
        date_param = request.query_params.get('date')
        if not date_param:
            return Response(
                {"error": "date parameter is required (YYYY-MM-DD format)"},
                status=400
            )

        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=400
            )

        # Use date-based filtering
        excluded_staff_ids = get_excluded_staff()
        staff = Staff.objects.active_on_date(target_date).exclude(
            Q(is_office_staff=True) | Q(id__in=excluded_staff_ids)
        ).order_by("last_name", "first_name")

        # ... rest of method
```

**Accounts Staff API** (`apps/accounts/views/staff_views.py`):

```python
class StaffListAPIView(generics.ListAPIView):
    def get_queryset(self):
        actual_users_param = self.request.GET.get("actual_users", "false").lower()
        date_param = self.request.GET.get("date")

        if date_param:
            try:
                target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
                base_queryset = Staff.objects.active_on_date(target_date)
            except ValueError:
                # Invalid date format, fall back to current active
                base_queryset = Staff.objects.currently_active()
        else:
            # Default to all staff for backward compatibility
            base_queryset = Staff.objects.all()

        if actual_users_param == "true":
            excluded_ids_str = get_excluded_staff()
            excluded_ids = [UUID(id_str) for id_str in excluded_ids_str]
            return base_queryset.exclude(id__in=excluded_ids)

        return base_queryset
```

### Phase 4: Update Utilities

#### get_excluded_staff Function

```python
# apps/accounts/utils.py
def get_excluded_staff(apps_registry: Optional[Any] = None) -> List[str]:
    # Update to use currently_active() instead of is_active=True
    staff_with_ids = Staff.objects.currently_active().values_list(
        "id",
        "ims_payroll_id",
        # ... rest of fields
    )
    # ... rest of function logic
```

## API Contract Changes

### Before

```
GET /timesheet/api/staff/              # Inconsistent filtering
GET /accounts/api/staff/all/           # All staff
GET /accounts/api/staff/all/?actual_users=true  # Filtered staff
```

### After

```
GET /timesheet/api/staff/?date=2024-01-15                    # Required date parameter
GET /accounts/api/staff/all/                                 # All staff (unchanged)
GET /accounts/api/staff/all/?date=2024-01-15                # Staff active on date
GET /accounts/api/staff/all/?date=2024-01-15&actual_users=true  # Filtered staff on date
```

## Benefits

1. **Single Source of Truth**: Employment status determined purely by date logic
2. **Historical Accuracy**: Can determine who was employed on any past date
3. **No Field Duplication**: Eliminates `is_active` / `date_left` redundancy
4. **Clean Architecture**: Date-based logic throughout the system
5. **Backward Compatibility**: Accounts API maintains existing behavior when no date provided

## Testing Strategy

1. **Migration Testing**: Verify data migration correctly sets `date_left` for inactive staff
2. **API Testing**: Test all combinations of date parameters and filtering
3. **Edge Cases**: Test boundary conditions (start date, end date, same day)
4. **Integration Testing**: Verify timesheet and form functionality with new filtering

## Rollback Plan

1. Run reverse migration to restore `is_active` field
2. Revert code changes to use `is_active` filtering
3. Remove `date_left` field if needed

## Implementation Order

1. Create and run migrations (0006, 0007, 0008)
2. Update Staff model and StaffManager
3. Update all `is_active` references throughout codebase
4. Update API endpoints
5. Update utilities and forms
6. Test all functionality
7. Run quality checks (tox)
