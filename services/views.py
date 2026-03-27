from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Service, Booking, IndividualBooking, EmployeeBooking, WorkplaceGovernanceBooking, PilotRequest
from .serializers import (
    ServiceSerializer, BookingSerializer, IndividualBookingSerializer,
    EmployeeBookingSerializer, WorkplaceGovernanceBookingSerializer, PilotRequestSerializer
)
from .permissions import IsServiceProviderOrAdmin, IsBookingOwnerOrStaff
from users.permissions import IsAdmin


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]  # Default to public access

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(provider=self.request.user)
        else:
            # For unauthenticated requests, we need a default provider
            from users.models import User
            admin_user = User.objects.filter(role='admin').first()
            serializer.save(provider=admin_user)

    def get_permissions(self):
        # Only restrict admin operations
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        # All other operations (list, retrieve) are public
        return [AllowAny()]


class IndividualBookingViewSet(viewsets.ModelViewSet):
    queryset = IndividualBooking.objects.all()
    serializer_class = IndividualBookingSerializer
    permission_classes = [AllowAny]  # Default to public access

    def get_permissions(self):
        # Only restrict admin operations
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        # Create operation is public
        return [AllowAny()]

    def perform_create(self, serializer):
        individual_booking = serializer.save()
        # Create related Booking record
        booking = Booking.objects.create(
            service=individual_booking.service,
            booking_type='individual',
            customer=None,
            status=individual_booking.status,
            subscription_type=individual_booking.subscription_type
        )
        individual_booking.booking = booking
        individual_booking.save()

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def admin_list(self, request):
        """Admin endpoint to view all individual bookings"""
        bookings = IndividualBooking.objects.all()
        serializer = IndividualBookingSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdmin])
    def update_status(self, request, pk=None):
        """Admin endpoint to update booking status"""
        booking = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'confirmed', 'cancelled']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = new_status
        booking.save()
        # Update related Booking record
        if booking.booking:
            booking.booking.status = new_status
            booking.booking.save()
        return Response(IndividualBookingSerializer(booking).data)


class EmployeeBookingViewSet(viewsets.ModelViewSet):
    queryset = EmployeeBooking.objects.all()
    serializer_class = EmployeeBookingSerializer
    permission_classes = [AllowAny]  # Default to public access

    def get_permissions(self):
        # Only restrict admin operations
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        # Create operation is public
        return [AllowAny()]

    def perform_create(self, serializer):
        employee_booking = serializer.save()
        # Create related Booking record
        booking = Booking.objects.create(
            service=employee_booking.service,
            booking_type='employee',
            customer=None,
            status=employee_booking.status,
            subscription_type=employee_booking.subscription_type
        )
        employee_booking.booking = booking
        employee_booking.save()

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def admin_list(self, request):
        """Admin endpoint to view all employee bookings"""
        bookings = EmployeeBooking.objects.all()
        serializer = EmployeeBookingSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdmin])
    def update_status(self, request, pk=None):
        """Admin endpoint to update booking status"""
        booking = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'confirmed', 'cancelled']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = new_status
        booking.save()
        # Update related Booking record
        if booking.booking:
            booking.booking.status = new_status
            booking.booking.save()
        return Response(EmployeeBookingSerializer(booking).data)


class WorkplaceGovernanceBookingViewSet(viewsets.ModelViewSet):
    queryset = WorkplaceGovernanceBooking.objects.all()
    serializer_class = WorkplaceGovernanceBookingSerializer
    permission_classes = [AllowAny]  # Default to public access

    def get_permissions(self):
        # Only restrict admin operations
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        # Create operation is public
        return [AllowAny()]

    def perform_create(self, serializer):
        workplace_booking = serializer.save()
        # Create related Booking record
        booking = Booking.objects.create(
            service=workplace_booking.service,
            booking_type='workplace_governance',
            customer=None,
            status=workplace_booking.status,
            subscription_type=workplace_booking.subscription_type
        )
        workplace_booking.booking = booking
        workplace_booking.save()

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def admin_list(self, request):
        """Admin endpoint to view all workplace governance bookings"""
        bookings = WorkplaceGovernanceBooking.objects.all()
        serializer = WorkplaceGovernanceBookingSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdmin])
    def update_status(self, request, pk=None):
        """Admin endpoint to update booking status"""
        booking = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'confirmed', 'cancelled']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = new_status
        booking.save()
        # Update related Booking record
        if booking.booking:
            booking.booking.status = new_status
            booking.booking.save()
        return Response(WorkplaceGovernanceBookingSerializer(booking).data)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            if self.request.user.role not in ['admin', 'staff']:
                queryset = queryset.filter(customer=self.request.user)
        return queryset

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        return [AllowAny()]

    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def admin_list(self, request):
        """Admin endpoint to view all bookings"""
        bookings = Booking.objects.all()
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdmin])
    def update_status(self, request, pk=None):
        """Admin endpoint to update booking status"""
        booking = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'confirmed', 'cancelled']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = new_status
        booking.save()
        return Response(BookingSerializer(booking).data)

class PilotRequestViewSet(viewsets.ModelViewSet):
    queryset = PilotRequest.objects.all()
    serializer_class = PilotRequestSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post', 'get']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAdmin()]
        elif self.action == 'create':
            return [AllowAny()]
        return [AllowAny()]
