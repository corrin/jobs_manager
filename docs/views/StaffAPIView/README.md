# Staff API Views Documentation

## Business Purpose

Provides REST API endpoints for staff management in jobbing shop operations. Handles staff CRUD operations, user account management, and personnel data synchronization. Essential for managing jobbing shop workforce, time tracking assignments, and user access control throughout the system.

## Views

### StaffListCreateAPIView

**File**: `apps/accounts/views/staff_api.py`
**Type**: Class-based view (ListCreateAPIView)
**URL**: `/accounts/api/staff/`

#### What it does

- Provides REST API endpoint for listing all staff members
- Handles creation of new staff accounts via API
- Supports both GET (list) and POST (create) operations
- Manages staff data with multipart form support for file uploads

#### Parameters

- **GET**: No parameters required - returns all staff
- **POST**: Staff creation data via form or JSON:
  - Personal information (first_name, last_name, email)
  - Account settings (password, permissions)
  - Profile data (icon, preferred_name)
  - Wage rates and billing information

#### Returns

- **200 OK**: JSON array of all staff members with complete data
- **201 Created**: Newly created staff member data
- **400 Bad Request**: Validation errors during staff creation
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Staff permissions required

#### Integration

- StaffSerializer for data validation and serialization
- IsAuthenticated and IsStaff permission classes
- MultiPartParser and FormParser for file upload support
- Staff model for data persistence

### StaffRetrieveUpdateDestroyAPIView

**File**: `apps/accounts/views/staff_api.py`
**Type**: Class-based view (RetrieveUpdateDestroyAPIView)
**URL**: `/accounts/api/staff/<uuid:pk>/`

#### What it does

- Provides REST API endpoint for individual staff management
- Supports GET (retrieve), PUT/PATCH (update), and DELETE (destroy) operations
- Handles partial updates for staff profile modifications
- Manages comprehensive staff data including permissions and rates

#### Parameters

- `pk`: Staff UUID identifier (path parameter)
- **PUT/PATCH**: Updated staff data:
  - Profile information updates
  - Permission and role changes
  - Wage rate modifications
  - Account status changes

#### Returns

- **200 OK**: Staff member data (GET) or updated data (PUT/PATCH)
- **204 No Content**: Successful deletion (DELETE)
- **400 Bad Request**: Validation errors during updates
- **404 Not Found**: Staff member not found
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Staff permissions required

#### Integration

- StaffSerializer for data validation and serialization
- Enhanced logging for staff update operations
- Password handling for security updates
- Permission management for access control

### update (Custom Update Method)

**File**: `apps/accounts/views/staff_api.py`
**Type**: Method override within StaffRetrieveUpdateDestroyAPIView

#### What it does

- Overrides default update behavior with enhanced logging
- Provides detailed audit trail for staff modifications
- Handles validation errors with comprehensive error reporting
- Manages partial updates for staff profile changes

#### Parameters

- Same as parent PUT/PATCH operations
- Enhanced logging for debugging and audit purposes

#### Returns

- Same return codes as parent class
- Enhanced error logging for troubleshooting
- Detailed audit trail in application logs

#### Integration

- Comprehensive logging system for audit trails
- Validation error handling and reporting
- Staff update workflow management
- Security and compliance tracking

## Error Handling

- **400 Bad Request**: Validation errors, invalid staff data, or malformed requests
- **401 Unauthorized**: Authentication required for all staff operations
- **403 Forbidden**: Staff-level permissions required for access
- **404 Not Found**: Staff member not found for individual operations
- **500 Internal Server Error**: System failures or database errors
- Comprehensive logging for debugging and audit trails
- Detailed error messages for API consumers

## Data Serialization

- StaffSerializer provides complete staff data structure
- Support for multipart form data and file uploads
- Password handling with secure hashing
- Permission and group management
- Wage rate and billing information

## Integration Points

- **Staff Model**: Core data persistence and user account management
- **Authentication System**: Permission-based access control
- **Permission Framework**: IsStaff permission for administrative access
- **File Upload System**: Profile image and document management
- **Audit System**: Comprehensive logging for compliance

## Business Rules

- Only authenticated staff can access staff management APIs
- Staff-level permissions required for all operations
- Password changes are handled securely with proper hashing
- Profile updates maintain data integrity and validation
- Deletion operations may be restricted based on business rules

## Security Considerations

- Authentication required for all endpoints
- Staff-level permissions enforce administrative access
- Password handling uses secure hashing algorithms
- File upload validation for profile images
- Audit logging for security monitoring

## Performance Considerations

- Efficient queryset handling for staff listings
- Optimized serialization for API responses
- Multipart parser support for file uploads
- Database indexing for UUID-based lookups
- Pagination support for large staff datasets

## Related Views

- Staff template views for web interface
- User profile views for individual account management
- Authentication views for login/logout functionality
- Permission management views for access control
