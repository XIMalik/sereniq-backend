from rest_framework import serializers
from .models import Service, Booking, IndividualBooking, EmployeeBooking, WorkplaceGovernanceBooking, PilotRequest

class ServiceSerializer(serializers.ModelSerializer):
    provider = serializers.StringRelatedField(read_only=True)
    provider_id = serializers.IntegerField(source='provider.id', read_only=True)
    service_type = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'duration', 'price', 'provider', 'provider_id', 'type', 'service_type', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_service_type(self, obj):
        """Determine service type for frontend grouping"""
        name = obj.name
        if '™' in name and 'Add-on' not in name and 'Bundle' not in name and 'Discount' not in name:
            return 'training'
        elif 'Bundle' in name or 'Discount' in name:
            return 'package'
        elif 'Add-on' in name:
            return 'addon'
        else:
            return 'other'

class IndividualBookingSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = IndividualBooking
        fields = ['id', 'name', 'email', 'phone', 'service', 'service_name', 'subscription_type', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        if self.instance is None:  # Creating new booking
            existing = IndividualBooking.objects.filter(
                email=data['email'],
                service=data['service'],
                status__in=['pending', 'confirmed']
            ).exists()
            if existing:
                raise serializers.ValidationError('You already have a pending or confirmed booking for this service')
        return data


class EmployeeBookingSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = EmployeeBooking
        fields = ['id', 'company_name', 'email', 'contact_person', 'number_of_employees', 'duration', 'service', 'service_name', 'subscription_type', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        if self.instance is None:  # Creating new booking
            existing = EmployeeBooking.objects.filter(
                email=data['email'],
                service=data['service'],
                status__in=['pending', 'confirmed']
            ).exists()
            if existing:
                raise serializers.ValidationError('Your company already has a pending or confirmed booking for this service')
        return data


class WorkplaceGovernanceBookingSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = WorkplaceGovernanceBooking
        fields = ['id', 'company_name', 'contact_person', 'phone_number', 'email', 'number_of_employees', 'subscription_type', 'service', 'service_name', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        if self.instance is None:  # Creating new booking
            existing = WorkplaceGovernanceBooking.objects.filter(
                email=data['email'],
                service=data['service'],
                status__in=['pending', 'confirmed']
            ).exists()
            if existing:
                raise serializers.ValidationError('Your company already has a pending or confirmed booking for this service')
        return data


class BookingSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    customer = serializers.StringRelatedField(read_only=True, allow_null=True)

    class Meta:
        model = Booking
        fields = ['id', 'service', 'service_name', 'booking_type', 'customer', 'subscription_type', 'status', 'created_at']
        read_only_fields = ['id', 'created_at', 'customer']


class PilotRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PilotRequest
        fields = ['id', 'name', 'company', 'role', 'email', 'workforce_size', 'challenge', 'created_at']
        read_only_fields = ['id', 'created_at']
