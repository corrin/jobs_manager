# Xero Authentication Views

## Business Purpose
Handles OAuth2 authentication flow with Xero accounting system. Manages secure token exchange, session state validation, and user authentication for accounting integration.

## Views

### xero_authenticate
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/authenticate/`

#### What it does
- Initiates OAuth2 authentication flow with Xero
- Generates secure state UUID for CSRF protection
- Stores authentication state in user session
- Redirects user to Xero's OAuth login page

#### Parameters
- `next`: Optional redirect URL after successful authentication (query parameter)

#### Returns
- **302 Redirect**: To Xero OAuth authorization URL with state parameter

#### Integration
- Uses get_authentication_url() for OAuth URL generation
- Session management for state validation and post-login redirects
- CSRF protection through state parameter validation

### xero_oauth_callback
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/callback/`

#### What it does
- Handles OAuth callback from Xero after user authorization
- Validates state parameter against session data
- Exchanges authorization code for access token
- Retrieves tenant connections and logs available organizations

#### Parameters
- `code`: OAuth authorization code (query parameter)
- `state`: State UUID for validation (query parameter)

#### Returns
- **302 Redirect**: To frontend URL or error page
- **200 OK**: Error template for authentication failures

#### Integration
- Uses exchange_code_for_token() for token exchange
- IdentityApi for tenant connection retrieval
- Frontend URL configuration for proper redirects
- Comprehensive error handling and logging

### refresh_xero_token
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/refresh/`

#### What it does
- Refreshes expired OAuth tokens automatically
- Handles token refresh failures gracefully
- Redirects to appropriate endpoints based on success/failure

#### Parameters
- No parameters required

#### Returns
- **302 Redirect**: To Xero index on success or authentication on failure

#### Integration
- Uses refresh_token() utility for token refresh logic
- Automatic fallback to re-authentication when refresh fails

### success_xero_connection
**File**: `apps/workflow/views/xero/xero_view.py`
**Type**: Function-based view with CSRF exemption
**URL**: `/workflow/xero/success/`

#### What it does
- Displays success page after Xero connection establishment
- Provides user feedback for successful authentication
- Serves as confirmation endpoint in OAuth flow

#### Parameters
- No parameters required

#### Returns
- **200 OK**: Success template confirming Xero connection

#### Integration
- Simple template view for user experience completion
- Part of OAuth success flow confirmation

## Error Handling
- OAuth state validation prevents CSRF attacks
- Token exchange failures redirect to error templates
- Comprehensive logging for debugging authentication issues
- Graceful fallback to re-authentication on token refresh failures

## Security Considerations
- CSRF protection through state parameter validation
- Secure session management for OAuth state
- Token storage and refresh handled by underlying utilities
- Frontend URL validation for safe redirects
