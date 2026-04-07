from django.db import models
from django.conf import settings


class Service(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    duration = models.PositiveIntegerField(help_text='Duration in days')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='services')
    created_at = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=20, default='training')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    BOOKING_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('employee', 'Employee'),
        ('workplace_governance', 'Workplace Governance'),
    ]

    SUBSCRIPTION_CHOICES = [
        ('subscription', 'Subscription'),
        ('pilot', 'Pilot'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    booking_type = models.CharField(max_length=25, choices=BOOKING_TYPE_CHOICES, default='individual')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='pilot')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking_type.title()} Booking - {self.service.name}"

    class Meta:
        ordering = ['-created_at']


class IndividualBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    SUBSCRIPTION_CHOICES = [
        ('subscription', 'Subscription'),
        ('pilot', 'Pilot'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='individual_booking', null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='individual_bookings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='pilot')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Individual Booking - {self.name}"

    class Meta:
        ordering = ['-created_at']


class EmployeeBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    SUBSCRIPTION_CHOICES = [
        ('subscription', 'Subscription'),
        ('pilot', 'Pilot'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='employee_booking', null=True, blank=True)
    company_name = models.CharField(max_length=255)
    email = models.EmailField()
    contact_person = models.CharField(max_length=255)
    number_of_employees = models.PositiveIntegerField()
    duration = models.PositiveIntegerField(help_text='Duration in minutes')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='employee_bookings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='pilot')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Employee Booking - {self.company_name}"

    class Meta:
        ordering = ['-created_at']


class WorkplaceGovernanceBooking(models.Model):
    SUBSCRIPTION_CHOICES = [
        ('subscription', 'Subscription'),
        ('pilot', 'Pilot'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='workplace_governance_booking', null=True, blank=True)
    company_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    number_of_employees = models.PositiveIntegerField()
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES, default='pilot')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='workplace_governance_bookings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Workplace Governance Booking - {self.company_name}"

    class Meta:
        ordering = ['-created_at']


class PilotRequest(models.Model):
    WORKFORCE_SIZE_CHOICES = [
        ('1-50', '1–50 employees'),
        ('51-200', '51–200 employees'),
        ('201-500', '201–500 employees'),
        ('500+', '500+ employees'),
    ]

    name = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    workforce_size = models.CharField(max_length=20, choices=WORKFORCE_SIZE_CHOICES, blank=True)
    challenge = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pilot Request - {self.name} ({self.company})"

    class Meta:
        ordering = ['-created_at']
