# Password View Documentation

## Business Purpose
Provides secure password management functionality for jobbing shop staff accounts. Extends Django's built-in password change system with custom templates and security requirements. Essential for maintaining account security and compliance with the system's minimum 10-character password policy.

## Views

### SecurityPasswordChangeView
**File**: `apps/accounts/views/password_views.py`
**Type**: Class-based view (PasswordChangeView)
**URL**: `/accounts/password_change/`

#### What it does
- Provides secure password change interface for authenticated staff
- Extends Django's PasswordChangeView with custom template
- Enforces jobbing shop security requirements and password validation
- Redirects users to success page after successful password change

#### Parameters
- Current password validation (required)
- New password with confirmation (required)
- Inherits Django's password validation rules plus custom 10-character minimum

#### Returns
- **200 OK**: Password change form template
- **302 Redirect**: To password change success page after successful update
- **Form Errors**: Validation errors for invalid passwords or mismatched confirmation

#### Integration
- Django's built-in PasswordChangeView for security foundation
- Custom template at `accounts/registration/password_change_form.html`
- Success redirect to `accounts:password_change_done` URL
- Password validation middleware for security requirements

## Error Handling
- **Form Validation Errors**: Invalid current password, weak new password, or confirmation mismatch
- **Authentication Required**: Only accessible to logged-in staff members
- Password strength validation according to system requirements (minimum 10 characters)
- Clear error messages for user guidance

## Integration Points
- **Authentication System**: Requires active user session
- **Password Validation**: Enforces system-wide password strength requirements
- **Template System**: Custom templates for consistent UI/UX
- **URL Routing**: Integrated with accounts app URL patterns

## Business Rules
- Only authenticated staff can change passwords
- Current password verification required for security
- New passwords must meet minimum 10-character requirement
- Password confirmation must match new password
- Successful changes redirect to confirmation page

## Security Considerations
- Current password verification prevents unauthorized changes
- Strong password requirements with 10-character minimum
- Secure password hashing and storage
- Session-based authentication required
- Protection against password change attacks

## Related Views
- Django's PasswordChangeDoneView for success confirmation
- Authentication views for login/logout functionality
- Staff management views for account administration
- User profile views for account settings