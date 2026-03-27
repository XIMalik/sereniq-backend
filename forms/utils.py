from .models import AccessKey
from datetime import datetime, timedelta
from django.utils import timezone
import uuid


def generate_access_key(company_name=None, has_pilot_access=True, has_sub_access=False, expires_in_days=None):
    """
    Generate a new access key
    
    Args:
        company_name (str, optional): Name of the company
        has_pilot_access (bool): Whether key has pilot access (default: True)
        has_sub_access (bool): Whether key has subscription access (default: False)
        expires_in_days (int, optional): Number of days until expiry
    
    Returns:
        AccessKey: The created access key object
    """
    expires_at = None
    if expires_in_days:
        expires_at = timezone.now() + timedelta(days=expires_in_days)
    
    access_key = AccessKey.objects.create(
        company_name=company_name,
        has_pilot_access=has_pilot_access,
        has_sub_access=has_sub_access,
        expires_at=expires_at
    )
    
    return access_key


def validate_access_key(key_string):
    """
    Validate an access key string
    
    Args:
        key_string (str): The access key string to validate
    
    Returns:
        AccessKey or None: The access key object if valid, None otherwise
    """
    try:
        # Convert string to UUID
        key_uuid = uuid.UUID(key_string)
        access_key = AccessKey.objects.get(key=key_uuid)
        
        if access_key.is_valid():
            return access_key
        return None
    except (ValueError, AccessKey.DoesNotExist):
        return None


def get_accessible_forms(access_key=None):
    """
    Get forms accessible based on access key
    
    Args:
        access_key (AccessKey, optional): The access key object
    
    Returns:
        dict: Dictionary with accessible form types and queryset
    """
    from .models import Form
    
    if not access_key:
        # No key provided - no access to any forms
        return {
            'forms': Form.objects.none(),
            'has_pilot_access': False,
            'has_sub_access': False
        }
    
    if access_key.has_sub_access:
        # Full access - all forms
        return {
            'forms': Form.objects.all(),
            'has_pilot_access': access_key.has_pilot_access,
            'has_sub_access': True
        }
    elif access_key.has_pilot_access:
        # Only pilot access
        return {
            'forms': Form.objects.filter(type='pilot'),
            'has_pilot_access': True,
            'has_sub_access': False
        }
    else:
        # No access
        return {
            'forms': Form.objects.none(),
            'has_pilot_access': False,
            'has_sub_access': False
        }