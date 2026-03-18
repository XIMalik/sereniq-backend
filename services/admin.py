from django.contrib import admin
from .models import Service, Booking, IndividualBooking, EmployeeBooking, WorkplaceGovernanceBooking


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'duration', 'price', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'service', 'booking_type', 'customer', 'subscription_type', 'status', 'created_at']
    list_filter = ['status', 'booking_type', 'subscription_type', 'created_at']
    search_fields = ['service__name', 'customer__email']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('service', 'booking_type', 'subscription_type', 'status', 'customer')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(IndividualBooking)
class IndividualBookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'phone', 'service', 'subscription_type', 'status', 'created_at']
    list_filter = ['status', 'subscription_type', 'created_at', 'service']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Booking Information', {
            'fields': ('service', 'subscription_type', 'status')
        }),
        ('Related Booking', {
            'fields': ('booking',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmployeeBooking)
class EmployeeBookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_name', 'contact_person', 'email', 'number_of_employees', 'subscription_type', 'status', 'created_at']
    list_filter = ['status', 'subscription_type', 'created_at', 'service']
    search_fields = ['company_name', 'email', 'contact_person']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'contact_person', 'email')
        }),
        ('Booking Details', {
            'fields': ('number_of_employees', 'duration', 'service', 'subscription_type', 'status')
        }),
        ('Related Booking', {
            'fields': ('booking',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkplaceGovernanceBooking)
class WorkplaceGovernanceBookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_name', 'contact_person', 'email', 'number_of_employees', 'subscription_type', 'status', 'created_at']
    list_filter = ['status', 'subscription_type', 'created_at', 'service']
    search_fields = ['company_name', 'email', 'contact_person', 'phone_number']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'contact_person', 'phone_number', 'email')
        }),
        ('Booking Details', {
            'fields': ('number_of_employees', 'service', 'subscription_type', 'status')
        }),
        ('Related Booking', {
            'fields': ('booking',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
