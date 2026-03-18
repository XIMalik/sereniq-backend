from rest_framework import permissions


class IsServiceProviderOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'admin':
            return True
        return obj.provider == request.user


class IsBookingOwnerOrStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.role in ['admin', 'staff']:
            return True
        return obj.customer == request.user
