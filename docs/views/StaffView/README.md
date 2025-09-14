# Staff Views Documentation

## Business Purpose

Provides comprehensive staff management functionality for jobbing shop operations. Handles staff CRUD operations, role-based access control, and personnel data management. Essential for managing jobbing shop workforce, time tracking assignments, user permissions, and wage rate administration throughout the system.

## Views

### StaffListAPIView

**File**: `apps/accounts/views/staff_views.py`
**Type**: Class-based view (ListAPIView)
**URL**: `/accounts/api/staff/all/`

#### What it does

- Provides REST API endpoint for retrieving staff member lists
- Supports filtering for actual active users vs all staff records
- Returns staff data optimized for kanban and UI components
- Handles staff member selection and assignment workflows

#### Parameters

- `actual_users`: Query parameter (boolean) to filter out excluded staff (default: false)

#### Returns

- **200 OK**: JSON array of staff members with kanban-optimized data
- **401 Unauthorized**: Authentication required

#### Integration

- KanbanStaffSerializer for optimized staff data structure
- get_excluded_staff utility for filtering inactive/excluded staff
- Authentication required for all staff access
- Request context for URL generation

### StaffListView

**File**: `apps/accounts/views/staff_views.py`
**Type**: Class-based view (ListView)
**URL**: `/accounts/staff/`

#### What it does

- Displays paginated list of all staff members in web interface
- Provides main staff management dashboard for administrators
- Supports staff overview and navigation to individual records
- Restricted to staff managers for administrative access

#### Parameters

- Standard pagination parameters

#### Returns

- **200 OK**: Staff list template with all staff data
- **403 Forbidden**: Access denied for non-staff managers

#### Integration

- Staff model for data retrieval
- LoginRequiredMixin for authentication
- UserPassesTestMixin for staff manager authorization
- Template-based interface for staff management

### StaffCreateView

**File**: `apps/accounts/views/staff_views.py`
**Type**: Class-based view (CreateView)
**URL**: `/accounts/staff/new/`

#### What it does

- Provides staff creation interface for new employee onboarding
- Handles staff account setup with form validation
- Manages initial staff data entry and account creation
- Restricted to staff managers for administrative control

#### Parameters

- Form data for new staff member creation:
  - Personal information (first_name, last_name, email)
  - Account credentials (password, permissions)
  - Employment details (wage_rate, roles)
  - Profile settings (preferred_name, icon)

#### Returns

- **200 OK**: Staff creation form template
- **302 Redirect**: To staff list after successful creation
- **403 Forbidden**: Access denied for non-staff managers

#### Integration

- StaffCreationForm for data validation and processing
- Staff model for account creation
- Authentication and permission validation
- Success redirect to staff list view

### StaffUpdateView

**File**: `apps/accounts/views/staff_views.py`
**Type**: Class-based view (UpdateView)
**URL**: `/accounts/staff/<uuid:pk>/`

#### What it does

- Provides staff profile editing interface
- Handles staff data updates with comprehensive validation
- Supports both administrative updates and self-service editing
- Manages wage rates, permissions, and profile changes

#### Parameters

- `pk`: Staff UUID identifier (path parameter)
- Form data for staff updates:
  - Profile information modifications
  - Permission and role changes
  - Wage rate adjustments
  - Account status updates

#### Returns

- **200 OK**: Staff update form template
- **302 Redirect**: To staff list after successful update
- **403 Forbidden**: Access denied for unauthorized users

#### Integration

- StaffChangeForm for update validation and processing
- Dual authorization: staff managers OR self-editing
- Staff model for data persistence
- Success redirect to staff list view

### get_staff_rates

**File**: `apps/accounts/views/staff_views.py`
**Type**: Function-based API view
**URL**: `/accounts/api/staff/rates/<uuid:staff_id>/`

#### What it does

- Retrieves wage rate information for specific staff members
- Provides financial data for timesheet and job costing calculations
- Supports payroll and billing rate management
- Restricted to staff managers for financial data access

#### Parameters

- `staff_id`: UUID of staff member to retrieve rates for (path parameter)

#### Returns

- **200 OK**: JSON with staff wage rate data
  - `wage_rate`: Current wage rate for payroll calculations
- **403 Forbidden**: Access denied for non-staff managers
- **404 Not Found**: Staff member not found

#### Integration

- Staff model wage rate data
- Staff manager permission validation
- Financial calculation support for timesheet system
- JSON response for API consumption

## Error Handling

- **401 Unauthorized**: Authentication required for all staff operations
- **403 Forbidden**: Staff manager permissions required for most operations
- **404 Not Found**: Staff member not found for individual operations
- **400 Bad Request**: Form validation errors during create/update operations
- Role-based access control with appropriate error responses
- Self-editing permissions for staff profile updates

## Authorization Rules

- **Staff Managers**: Full access to all staff management operations
- **Individual Staff**: Can update their own profile records
- **General Staff**: Limited read access through API endpoints
- Authentication required for all staff-related operations
- Hierarchical permission system for administrative control

## Data Serialization

- KanbanStaffSerializer for API responses with optimized staff data
- StaffCreationForm and StaffChangeForm for web interface validation
- Wage rate data protection with manager-only access
- Profile image and icon management support

## Integration Points

- **Authentication System**: Login required with role-based permissions
- **Staff Model**: Core user account and profile data management
- **Form System**: StaffCreationForm and StaffChangeForm for validation
- **Timesheet System**: Wage rate integration for payroll calculations
- **Kanban System**: Staff assignment and filtering support

## Business Rules

- Only staff managers can create, update, or delete staff accounts
- Staff members can edit their own profiles (except sensitive data)
- Wage rate information restricted to managers for financial security
- Staff filtering supports active vs inactive user management
- Account creation requires comprehensive validation and setup

## Security Considerations

- Authentication required for all staff management operations
- Role-based access control with staff manager permissions
- Wage rate data protection from unauthorized access
- Profile update validation to prevent privilege escalation
- Audit trail for staff account modifications

## Performance Considerations

- Efficient staff filtering with excluded staff utility
- Optimized serialization for kanban and UI components
- Database indexing for UUID-based staff lookups
- Pagination support for large staff datasets
- Request context optimization for URL generation

## Related Views

- Staff API views for REST-based staff management
- User profile views for individual account settings
- Authentication views for login/logout functionality
- Timesheet views for staff time tracking integration
