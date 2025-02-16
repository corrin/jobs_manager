from django import template
from django.core.cache import cache
from datetime import datetime, timedelta, timezone

from workflow.models import CompanyDefaults

register = template.Library()

@register.simple_tag
def get_xero_action():
    """
    Returns the appropriate Xero action based on connection state.
    Returns:
        dict: Contains 'action_text' (str) and 'url_name' (str)
    """
    token = cache.get('xero_token')
    
    if not token or not token.get('access_token'):
        return {
            'action_text': 'Connect to Xero',
            'url_name': 'authenticate_xero'
        }
    
    expires_at = token.get('expires_at')
    if expires_at and datetime.fromtimestamp(expires_at, tz=timezone.utc) < datetime.now(timezone.utc):
        return {
            'action_text': 'Reconnect to Xero',
            'url_name': 'authenticate_xero'
        }
    
    return {
        'action_text': 'Disconnect from Xero',
        'url_name': 'xero_disconnect'
    }

@register.simple_tag
def check_xero_sync_needed():
    """
    Checks if Xero sync is needed (hasn't been run in over 24 hours)
    or if deep sync is needed (hasn't been run in over 30 days).
    Returns:
        dict: Contains 'needed' (bool) and 'message' (str)
    """
    try:
        company_defaults = CompanyDefaults.objects.first()
        now = datetime.now(timezone.utc)

        if not company_defaults or not company_defaults.last_xero_sync:
            return {
                'needed': True,
                'message': 'Xero data has never been synchronized'
            }
        
        # Check regular sync (24 hours)
        if now - company_defaults.last_xero_sync > timedelta(days=1):
            return {
                'needed': True,
                'message': 'Xero data is outdated, please run a Xero sync'
            }

        # Check deep sync (30 days)
        if not company_defaults.last_xero_deep_sync or (
            now - company_defaults.last_xero_deep_sync > timedelta(days=30)
        ):
            return {
                'needed': True,
                'message': 'Deep Xero sync needed (looking back 90 days)'
            }
        
        return {
            'needed': False,
            'message': None
        }
    except Exception:
        return {
            'needed': False,
            'message': None
        }