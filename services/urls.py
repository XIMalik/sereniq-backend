from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServiceViewSet, BookingViewSet, IndividualBookingViewSet,
    EmployeeBookingViewSet, WorkplaceGovernanceBookingViewSet, PilotRequestViewSet
)

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'bookings', BookingViewSet, basename='booking')

# Register booking types with different prefixes to avoid conflicts
router.register(r'individual-bookings', IndividualBookingViewSet, basename='individual-booking')
router.register(r'employee-bookings', EmployeeBookingViewSet, basename='employee-booking')
router.register(r'workplace-governance-bookings', WorkplaceGovernanceBookingViewSet, basename='workplace-governance-booking')
router.register(r'request-a-pilot', PilotRequestViewSet, basename='pilot-request')

urlpatterns = [
    path('', include(router.urls)),
]
