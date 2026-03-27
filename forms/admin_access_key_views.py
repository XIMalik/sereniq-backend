from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import AccessKey
from .serializers import AccessKeySerializer, AccessKeyAdminSerializer
from .utils import generate_access_key
from users.permissions import IsAdmin


class AccessKeyAdminViewSet(viewsets.ModelViewSet):
    """Admin-only viewset for managing access keys"""
    queryset = AccessKey.objects.all()
    serializer_class = AccessKeyAdminSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        """Filter and order access keys for admin view"""
        queryset = super().get_queryset()
        
        # Filter by active status if specified
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by access type
        access_type = self.request.query_params.get('access_type')
        if access_type == 'pilot_only':
            queryset = queryset.filter(has_pilot_access=True, has_sub_access=False)
        elif access_type == 'full_access':
            queryset = queryset.filter(has_sub_access=True)
        elif access_type == 'no_access':
            queryset = queryset.filter(has_pilot_access=False, has_sub_access=False)
        
        # Filter by expiry status
        expiry_status = self.request.query_params.get('expiry_status')
        now = timezone.now()
        if expiry_status == 'expired':
            queryset = queryset.filter(expires_at__lt=now)
        elif expiry_status == 'expiring_soon':
            # Expiring within 7 days
            soon = now + timedelta(days=7)
            queryset = queryset.filter(expires_at__gte=now, expires_at__lte=soon)
        elif expiry_status == 'never_expires':
            queryset = queryset.filter(expires_at__isnull=True)
        
        # Search by company name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(company_name__icontains=search)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def generate_key(self, request):
        """Generate a new access key"""
        company_name = request.data.get('company_name')
        has_pilot_access = request.data.get('has_pilot_access', True)
        has_sub_access = request.data.get('has_sub_access', False)
        expires_in_days = request.data.get('expires_in_days')
        
        if not company_name:
            return Response(
                {'error': 'Company name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            access_key = generate_access_key(
                company_name=company_name,
                has_pilot_access=has_pilot_access,
                has_sub_access=has_sub_access,
                expires_in_days=expires_in_days
            )
            
            return Response(
                AccessKeySerializer(access_key).data, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate access key: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        """Toggle active status of an access key"""
        access_key = self.get_object()
        access_key.is_active = not access_key.is_active
        access_key.save()
        
        return Response({
            'message': f'Access key {"activated" if access_key.is_active else "deactivated"}',
            'is_active': access_key.is_active
        })
    
    @action(detail=True, methods=['patch'])
    def extend_expiry(self, request, pk=None):
        """Extend expiry date of an access key"""
        access_key = self.get_object()
        days_to_extend = request.data.get('days', 30)
        
        if not isinstance(days_to_extend, int) or days_to_extend <= 0:
            return Response(
                {'error': 'Days must be a positive integer'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if access_key.expires_at:
            # Extend from current expiry date
            access_key.expires_at = access_key.expires_at + timedelta(days=days_to_extend)
        else:
            # Set expiry from now
            access_key.expires_at = timezone.now() + timedelta(days=days_to_extend)
        
        access_key.save()
        
        return Response({
            'message': f'Access key expiry extended by {days_to_extend} days',
            'expires_at': access_key.expires_at
        })
    
    @action(detail=True, methods=['patch'])
    def update_permissions(self, request, pk=None):
        """Update access permissions for a key"""
        access_key = self.get_object()
        
        has_pilot_access = request.data.get('has_pilot_access')
        has_sub_access = request.data.get('has_sub_access')
        
        if has_pilot_access is not None:
            access_key.has_pilot_access = has_pilot_access
        
        if has_sub_access is not None:
            access_key.has_sub_access = has_sub_access
        
        access_key.save()
        
        return Response({
            'message': 'Access permissions updated',
            'has_pilot_access': access_key.has_pilot_access,
            'has_sub_access': access_key.has_sub_access
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get access key statistics"""
        total_keys = AccessKey.objects.count()
        active_keys = AccessKey.objects.filter(is_active=True).count()
        inactive_keys = total_keys - active_keys
        
        # Access type breakdown
        pilot_only = AccessKey.objects.filter(
            has_pilot_access=True, 
            has_sub_access=False,
            is_active=True
        ).count()
        
        full_access = AccessKey.objects.filter(
            has_sub_access=True,
            is_active=True
        ).count()
        
        no_access = AccessKey.objects.filter(
            has_pilot_access=False,
            has_sub_access=False,
            is_active=True
        ).count()
        
        # Expiry breakdown
        now = timezone.now()
        expired = AccessKey.objects.filter(
            expires_at__lt=now,
            is_active=True
        ).count()
        
        expiring_soon = AccessKey.objects.filter(
            expires_at__gte=now,
            expires_at__lte=now + timedelta(days=7),
            is_active=True
        ).count()
        
        never_expires = AccessKey.objects.filter(
            expires_at__isnull=True,
            is_active=True
        ).count()
        
        return Response({
            'total_keys': total_keys,
            'active_keys': active_keys,
            'inactive_keys': inactive_keys,
            'access_types': {
                'pilot_only': pilot_only,
                'full_access': full_access,
                'no_access': no_access
            },
            'expiry_status': {
                'expired': expired,
                'expiring_soon': expiring_soon,
                'never_expires': never_expires
            }
        })
    
    @action(detail=False, methods=['post'])
    def bulk_generate(self, request):
        """Generate multiple access keys at once"""
        keys_data = request.data.get('keys', [])
        
        if not keys_data or not isinstance(keys_data, list):
            return Response(
                {'error': 'Keys data must be a non-empty array'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(keys_data) > 50:
            return Response(
                {'error': 'Cannot generate more than 50 keys at once'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_keys = []
        errors = []
        
        for i, key_data in enumerate(keys_data):
            try:
                company_name = key_data.get('company_name')
                if not company_name:
                    errors.append(f'Row {i+1}: Company name is required')
                    continue
                
                access_key = generate_access_key(
                    company_name=company_name,
                    has_pilot_access=key_data.get('has_pilot_access', True),
                    has_sub_access=key_data.get('has_sub_access', False),
                    expires_in_days=key_data.get('expires_in_days')
                )
                created_keys.append(AccessKeySerializer(access_key).data)
                
            except Exception as e:
                errors.append(f'Row {i+1}: {str(e)}')
        
        return Response({
            'created_keys': created_keys,
            'errors': errors,
            'summary': {
                'total_requested': len(keys_data),
                'successfully_created': len(created_keys),
                'failed': len(errors)
            }
        })
    
    @action(detail=False, methods=['post'])
    def bulk_update_status(self, request):
        """Bulk activate/deactivate access keys"""
        key_ids = request.data.get('key_ids', [])
        is_active = request.data.get('is_active')
        
        if not key_ids or not isinstance(key_ids, list):
            return Response(
                {'error': 'key_ids must be a non-empty array'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if is_active is None:
            return Response(
                {'error': 'is_active field is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = AccessKey.objects.filter(
            id__in=key_ids
        ).update(is_active=is_active)
        
        return Response({
            'message': f'{updated_count} access keys {"activated" if is_active else "deactivated"}',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        """Bulk delete access keys"""
        key_ids = request.data.get('key_ids', [])
        
        if not key_ids or not isinstance(key_ids, list):
            return Response(
                {'error': 'key_ids must be a non-empty array'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deleted_count, _ = AccessKey.objects.filter(
            id__in=key_ids
        ).delete()
        
        return Response({
            'message': f'{deleted_count} access keys deleted',
            'deleted_count': deleted_count
        })