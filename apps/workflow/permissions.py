"""
Custom permission classes for the workflow app.

SECURITY WARNING: This module contains development-only permission classes
that bypass authentication when DEBUG=True. These should NEVER be used in
production environments.
"""

from django.conf import settings
from rest_framework.permissions import BasePermission


class DevelopmentOrAuthenticatedPermission(BasePermission):
    """
    Permission class that allows unauthenticated access in development (DEBUG=True)
    but requires authentication in all other environments.
    
    SECURITY WARNING: This permission class is designed for development testing only.
    It bypasses authentication when DEBUG=True, which should NEVER be the case in
    production environments.
    
    This ensures:
    - Local development: Can test APIs without authentication when DEBUG=True
    - Production/UAT: Always requires authentication when DEBUG=False
    - No risk of accidentally disabling auth in production (as long as DEBUG=False)
    
    Usage:
        class MyDevelopmentAPIView(APIView):
            # DEVELOPMENT ONLY: Remove this permission class before production release
            # This allows testing without authentication when DEBUG=True
            permission_classes = [DevelopmentOrAuthenticatedPermission]
            
            def get(self, request, *args, **kwargs):
                # API implementation
                pass
    
    Important Notes:
    - Production environments MUST have DEBUG=False
    - This permission class should be removed before production deployment
    - Any usage requires code review and explicit documentation
    - Include clear comments about development-only usage in views
    """
    
    def has_permission(self, request, view):
        # Development mode: Allow all requests when DEBUG=True
        if settings.DEBUG:
            return True
        
        # Production mode: Require authentication
        return request.user.is_authenticated