from django.contrib.auth.backends import BaseBackend
from django.http import JsonResponse
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import ServiceAPIKey


class ServiceAPIKeyAuthentication(BaseAuthentication):
    """
    Authentication for service API keys (e.g., MCP endpoints).
    Looks for 'X-API-Key' header.
    """
    
    def authenticate(self, request):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return None  # No API key provided, skip this authentication
        
        try:
            service_key = ServiceAPIKey.objects.get(key=api_key, is_active=True)
            service_key.mark_used()
            
            # Return a tuple of (user, auth) - we don't have a user for service keys
            # so we return the service key object as the "user" for authorization checks
            return (service_key, None)
            
        except ServiceAPIKey.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'X-API-Key'


def service_api_key_required(view_func):
    """
    Decorator to require service API key authentication for a view.
    Simple alternative to DRF authentication classes.
    """
    def _wrapped_view(request, *args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return JsonResponse({'error': 'API key required'}, status=401)
        
        try:
            service_key = ServiceAPIKey.objects.get(key=api_key, is_active=True)
            service_key.mark_used()
            
            # Add the service key to the request for use in the view
            request.service_key = service_key
            
        except ServiceAPIKey.DoesNotExist:
            return JsonResponse({'error': 'Invalid API key'}, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view