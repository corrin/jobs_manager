# User Profile View Documentation

## Business Purpose
Provides user profile management and authentication lifecycle support for jobbing shop staff. Handles user profile retrieval for authenticated sessions and secure logout functionality with JWT token cleanup. Essential for user session management, profile information access, and secure authentication lifecycle in the jobbing shop management system.

## Views

### get_current_user
**File**: `apps/accounts/views/user_profile_view.py`
**Type**: Function-based API view (GET only)
**URL**: `/accounts/me/`

#### What it does
- Retrieves current authenticated user profile information
- Provides user details for UI personalization and access control
- Supports JWT authentication via httpOnly cookies or headers
- Returns comprehensive user profile data for application interfaces
- Enables user identity verification and profile display

#### Parameters
- No parameters required - uses authenticated user from request context

#### Returns
- **200 OK**: JSON with current user profile data
  - `id`: User UUID identifier
  - `username`: User email address
  - `email`: User email address
  - `first_name`: User first name
  - `last_name`: User last name
  - `preferred_name`: User preferred display name
  - `fullName`: Computed full name
  - `is_active`: Account active status
  - `is_staff`: Staff status for permissions
- **401 Unauthorized**: Authentication required
- **500 Internal Server Error**: Profile retrieval failures

#### Integration
- UserProfileSerializer for consistent profile data structure
- JWT authentication via httpOnly cookies or authorization headers
- Staff model for user account data
- Request context for URL generation and personalization

### logout_user
**File**: `apps/accounts/views/user_profile_view.py`
**Type**: Function-based API view (POST only)
**URL**: `/accounts/logout/`

#### What it does
- Provides secure logout functionality with JWT token cleanup
- Clears httpOnly cookies containing authentication tokens
- Handles both access and refresh token cleanup
- Supports clean session termination for security
- Manages logout for both cookie-based and header-based authentication

#### Parameters
- No parameters required - operates on current session

#### Returns
- **200 OK**: JSON confirmation of successful logout
  - `success`: Boolean success indicator
  - `message`: Logout confirmation message
- **500 Internal Server Error**: Logout processing failures

#### Integration
- JWT settings configuration for cookie names and domains
- httpOnly cookie management for secure token cleanup
- Response cookie deletion with proper domain and SameSite settings
- Authentication system integration for session termination

## Error Handling
- **401 Unauthorized**: Authentication required for profile access
- **500 Internal Server Error**: System failures during profile retrieval or logout
- Comprehensive error logging for debugging authentication issues
- User-friendly error messages for API consumers
- Graceful handling of token cleanup failures

## Security Features
- **Authentication Required**: Profile access requires valid JWT authentication
- **httpOnly Cookie Cleanup**: Secure removal of authentication tokens
- **Domain-Specific Cookie Deletion**: Proper cookie cleanup across domains
- **SameSite Cookie Handling**: CSRF protection during logout
- **Error Message Security**: Non-revealing error messages to prevent information leakage

## Data Serialization
- UserProfileSerializer provides comprehensive user profile structure
- Read-only profile data to prevent unauthorized modifications
- Computed fields like fullName for UI convenience
- Request context integration for personalized responses

## Integration Points
- **JWT Authentication**: Token-based authentication via cookies or headers
- **Staff Model**: User account data and profile information
- **Authentication Middleware**: Session management and user context
- **Frontend Applications**: Profile data for UI personalization

## Business Rules
- Only authenticated users can access their profile information
- Profile data is read-only via this endpoint
- Logout clears all authentication tokens for security
- User identity is derived from authenticated session context
- Profile access supports both cookie and header-based authentication

## Performance Considerations
- Efficient user profile serialization
- Minimal database queries for profile data
- Optimized cookie cleanup operations
- Cached JWT settings for quick access
- Single-query user profile retrieval

## Security Considerations
- Authentication required for all operations
- Secure token cleanup during logout
- httpOnly cookie handling prevents XSS attacks
- Proper cookie domain and SameSite configuration
- Error handling prevents information disclosure

## Related Views
- Token views for authentication and token management
- Staff views for comprehensive user account management
- Authentication middleware for request processing
- Password views for security management