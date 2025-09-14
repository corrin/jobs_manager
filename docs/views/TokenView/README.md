# Token View Documentation

## Business Purpose

Provides secure JWT token management for jobbing shop authentication system. Handles token-based authentication with enhanced security features including httpOnly cookies, password reset enforcement, and secure token handling. Essential for API access, mobile applications, and enhanced security posture of the jobbing shop management system.

## Views

### CustomTokenObtainPairView

**File**: `apps/accounts/views/token_view.py`
**Type**: Class-based view (TokenObtainPairView)
**URL**: `/accounts/api/token/`

#### What it does

- Provides JWT token authentication with enhanced security features
- Handles password reset requirement enforcement
- Sets JWT tokens as secure httpOnly cookies when enabled
- Validates user credentials and generates access/refresh token pairs
- Supports both API token authentication and cookie-based authentication

#### Parameters

- JSON body with authentication credentials:
  - `username`: User email address (required)
  - `password`: User password (required)

#### Returns

- **200 OK**: JSON with JWT tokens and user authentication data
  - `access`: JWT access token (or set as httpOnly cookie)
  - `refresh`: JWT refresh token (or set as httpOnly cookie)
  - `password_needs_reset`: Boolean flag for forced password reset
  - `password_reset_url`: URL for password change if reset required
- **401 Unauthorized**: Invalid credentials or authentication failure
- **400 Bad Request**: Malformed request or missing required fields

#### Integration

- CustomTokenObtainPairSerializer for enhanced credential validation
- JWT configuration from Django settings
- Password reset enforcement workflow
- httpOnly cookie security when ENABLE_JWT_AUTH is configured
- User model integration for account status checking

### CustomTokenRefreshView

**File**: `apps/accounts/views/token_view.py`
**Type**: Class-based view (TokenRefreshView)
**URL**: `/accounts/api/token/refresh/`

#### What it does

- Refreshes JWT access tokens using valid refresh tokens
- Supports both cookie-based and request body refresh tokens
- Provides seamless token renewal for continuous authentication
- Maintains httpOnly cookie security for token storage
- Handles token lifecycle management

#### Parameters

- **Option 1**: JSON body with refresh token:
  - `refresh`: Valid JWT refresh token (required)
- **Option 2**: httpOnly cookie containing refresh token
  - Automatically extracted from `refresh_token` cookie

#### Returns

- **200 OK**: JSON with new access token
  - `access`: New JWT access token (or set as httpOnly cookie)
- **401 Unauthorized**: Invalid or expired refresh token
- **400 Bad Request**: Missing refresh token or malformed request

#### Integration

- JWT settings configuration for token lifetime and security
- httpOnly cookie handling for secure token storage
- Automatic token extraction from cookies or request body
- Access token renewal workflow

### post (CustomTokenObtainPairView)

**File**: `apps/accounts/views/token_view.py`
**Type**: Method override within CustomTokenObtainPairView

#### What it does

- Overrides default token obtain behavior with enhanced security
- Implements password reset requirement checking
- Manages JWT cookie configuration and security settings
- Provides comprehensive logging for authentication events
- Handles user account status validation

#### Parameters

- Same as parent CustomTokenObtainPairView
- Enhanced processing for security features

#### Returns

- Enhanced token response with security features
- Password reset enforcement when required
- Comprehensive audit logging

#### Integration

- User model password reset status checking
- Django settings integration for JWT configuration
- Security enhancement with httpOnly cookies
- Audit trail for authentication events

### post (CustomTokenRefreshView)

**File**: `apps/accounts/views/token_view.py`
**Type**: Method override within CustomTokenRefreshView

#### What it does

- Overrides default token refresh with cookie support
- Handles refresh token extraction from multiple sources
- Manages access token renewal with security features
- Provides seamless token refresh experience

#### Parameters

- Enhanced refresh token handling from cookies or request body
- Automatic token source detection

#### Returns

- Refreshed access token with security features
- httpOnly cookie management for token storage

#### Integration

- Cookie-based token storage and retrieval
- JWT settings integration for security configuration
- Token lifecycle management

## Error Handling

- **400 Bad Request**: Missing credentials, malformed requests, or invalid token format
- **401 Unauthorized**: Invalid credentials, expired tokens, or authentication failures
- **404 Not Found**: User account not found during authentication
- **500 Internal Server Error**: System failures or configuration errors
- Comprehensive logging for debugging authentication issues
- Security-focused error messages to prevent information leakage

## Security Features

- **httpOnly Cookies**: Secure token storage preventing XSS attacks
- **Secure Cookie Flags**: HTTPS-only transmission for production security
- **SameSite Protection**: CSRF protection through cookie configuration
- **Password Reset Enforcement**: Required password changes for security compliance
- **Token Lifetime Management**: Configurable token expiration for security
- **Audit Logging**: Comprehensive authentication event tracking

## Integration Points

- **JWT Configuration**: Django settings for token security and lifetime
- **User Model**: Staff account integration for authentication
- **Password Management**: Password reset workflow integration
- **Cookie Security**: httpOnly and secure cookie configuration
- **API Authentication**: Token-based API access control

## Business Rules

- Username field maps to user email address for authentication
- Password reset requirement blocks normal authentication flow
- JWT tokens can be stored as httpOnly cookies or returned in response body
- Token refresh requires valid refresh token from cookie or request body
- Authentication events are logged for security monitoring

## Configuration Options

- `ENABLE_JWT_AUTH`: Enable httpOnly cookie-based token storage
- `SIMPLE_JWT`: JWT token configuration including lifetime and security settings
- `COOKIE_SAMESITE`: Environment-based SameSite cookie configuration
- Token lifetime configuration for access and refresh tokens
- Cookie domain and security flag configuration

## Performance Considerations

- Efficient JWT token generation and validation
- Optimized cookie handling and configuration
- Minimal database queries for user authentication
- Cached JWT settings for quick access
- Efficient token refresh workflow

## Related Views

- User profile views for account management
- Password change views for security compliance
- Authentication middleware for request processing
- API views requiring JWT authentication
