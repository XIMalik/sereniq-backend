from django.core.management.base import BaseCommand
from django.utils import timezone
from forms.models import AccessKey
from datetime import timedelta


class Command(BaseCommand):
    help = 'List and manage access keys'

    def add_arguments(self, parser):
        parser.add_argument(
            '--filter',
            choices=['active', 'inactive', 'expired', 'expiring-soon', 'pilot-only', 'full-access'],
            help='Filter keys by status or access type'
        )
        parser.add_argument(
            '--search',
            type=str,
            help='Search by company name'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show statistics only'
        )
        parser.add_argument(
            '--deactivate',
            type=str,
            help='Deactivate key by UUID'
        )
        parser.add_argument(
            '--activate',
            type=str,
            help='Activate key by UUID'
        )

    def handle(self, *args, **options):
        if options['deactivate']:
            self.deactivate_key(options['deactivate'])
            return
        
        if options['activate']:
            self.activate_key(options['activate'])
            return
        
        if options['stats']:
            self.show_stats()
            return
        
        self.list_keys(options)

    def list_keys(self, options):
        queryset = AccessKey.objects.all()
        
        # Apply filters
        filter_type = options.get('filter')
        now = timezone.now()
        
        if filter_type == 'active':
            queryset = queryset.filter(is_active=True)
        elif filter_type == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif filter_type == 'expired':
            queryset = queryset.filter(expires_at__lt=now)
        elif filter_type == 'expiring-soon':
            soon = now + timedelta(days=7)
            queryset = queryset.filter(expires_at__gte=now, expires_at__lte=soon)
        elif filter_type == 'pilot-only':
            queryset = queryset.filter(has_pilot_access=True, has_sub_access=False)
        elif filter_type == 'full-access':
            queryset = queryset.filter(has_sub_access=True)
        
        # Apply search
        search = options.get('search')
        if search:
            queryset = queryset.filter(company_name__icontains=search)
        
        keys = queryset.order_by('-created_at')
        
        if not keys.exists():
            self.stdout.write(self.style.WARNING('No access keys found'))
            return
        
        self.stdout.write(f'Found {keys.count()} access key(s):\n')
        
        for key in keys:
            self.display_key(key)

    def display_key(self, key):
        # Status
        status = self.get_key_status(key)
        status_color = self.get_status_color(status)
        
        # Access level
        if key.has_sub_access:
            access_level = 'Full Access'
        elif key.has_pilot_access:
            access_level = 'Pilot Only'
        else:
            access_level = 'No Access'
        
        # Expiry
        if key.expires_at:
            if key.expires_at < timezone.now():
                expiry = f"Expired on {key.expires_at.strftime('%Y-%m-%d')}"
            else:
                days_left = (key.expires_at - timezone.now()).days
                expiry = f"Expires in {days_left} days ({key.expires_at.strftime('%Y-%m-%d')})"
        else:
            expiry = "Never expires"
        
        self.stdout.write(f'Company: {key.company_name}')
        self.stdout.write(f'Key: {key.key}')
        self.stdout.write(f'Status: {status_color(status)}')
        self.stdout.write(f'Access: {access_level}')
        self.stdout.write(f'Expiry: {expiry}')
        self.stdout.write(f'Created: {key.created_at.strftime("%Y-%m-%d %H:%M")}')
        self.stdout.write('-' * 50)

    def get_key_status(self, key):
        if not key.is_active:
            return 'Inactive'
        elif key.expires_at and key.expires_at < timezone.now():
            return 'Expired'
        elif key.expires_at and (key.expires_at - timezone.now()).days <= 7:
            return 'Expiring Soon'
        else:
            return 'Active'

    def get_status_color(self, status):
        if status == 'Active':
            return self.style.SUCCESS
        elif status == 'Expiring Soon':
            return self.style.WARNING
        elif status in ['Expired', 'Inactive']:
            return self.style.ERROR
        else:
            return lambda x: x

    def show_stats(self):
        total = AccessKey.objects.count()
        active = AccessKey.objects.filter(is_active=True).count()
        inactive = total - active
        
        # Access types (active only)
        pilot_only = AccessKey.objects.filter(
            has_pilot_access=True, 
            has_sub_access=False,
            is_active=True
        ).count()
        
        full_access = AccessKey.objects.filter(
            has_sub_access=True,
            is_active=True
        ).count()
        
        # Expiry status (active only)
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
        
        self.stdout.write(self.style.SUCCESS('Access Key Statistics'))
        self.stdout.write('=' * 30)
        self.stdout.write(f'Total Keys: {total}')
        self.stdout.write(f'Active: {active}')
        self.stdout.write(f'Inactive: {inactive}')
        self.stdout.write('')
        self.stdout.write('Access Types (Active Keys):')
        self.stdout.write(f'  Pilot Only: {pilot_only}')
        self.stdout.write(f'  Full Access: {full_access}')
        self.stdout.write('')
        self.stdout.write('Expiry Status (Active Keys):')
        self.stdout.write(f'  Expired: {expired}')
        self.stdout.write(f'  Expiring Soon (7 days): {expiring_soon}')
        self.stdout.write(f'  Never Expires: {never_expires}')

    def deactivate_key(self, key_uuid):
        try:
            key = AccessKey.objects.get(key=key_uuid)
            key.is_active = False
            key.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deactivated key for {key.company_name}')
            )
        except AccessKey.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Access key not found: {key_uuid}')
            )

    def activate_key(self, key_uuid):
        try:
            key = AccessKey.objects.get(key=key_uuid)
            key.is_active = True
            key.save()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully activated key for {key.company_name}')
            )
        except AccessKey.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Access key not found: {key_uuid}')
            )