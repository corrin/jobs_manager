from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy


class SecurityPasswordChangeView(PasswordChangeView):
    """
    Custom password change view with enhanced security requirements.
    
    This view extends Django's built-in PasswordChangeView to provide
    password change functionality with custom templates and success redirect.
    Enforces the application's password strength requirements.
    """
    template_name = "accounts/registration/password_change_form.html"
    success_url = reverse_lazy("accounts:password_change_done")
