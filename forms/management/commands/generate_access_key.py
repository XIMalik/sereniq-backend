from django.core.management.base import BaseCommand, CommandError
from forms.utils import generate_access_key
from forms.models import AccessKey


class Command(BaseCommand):
    help = 'Generate access keys for companies'

    def add_arguments(self, parser):
        parser.add_argument(
            'company_name',
            type=str,
            help='Name of the company'
        )
        parser.add_argument(
            '--pilot-access',
            action='store_true',
            default=True,
            help='Grant pilot access (default: True)'
        )
        parser.add_argument(
            '--sub-access',
            action='store_true',
            default=False,
            help='Grant subscription access (default: False)'
        )
        parser.add_argument(
            '--expires-in-days',
            type=int,
            help='Number of days until expiry (optional)'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=1,
            help='Number of keys to generate (default: 1)'
        )

    def handle(self, *args, **options):
        company_name = options['company_name']
        has_pilot_access = options['pilot_access']
        has_sub_access = options['sub_access']
        expires_in_days = options['expires_in_days']
        count = options['count']

        if count < 1 or count > 100:
            raise CommandError('Count must be between 1 and 100')

        self.stdout.write(
            self.style.SUCCESS(f'Generating {count} access key(s) for "{company_name}"...')
        )

        generated_keys = []
        
        for i in range(count):
            try:
                # Add number suffix if generating multiple keys
                name = company_name if count == 1 else f"{company_name} #{i+1}"
                
                access_key = generate_access_key(
                    company_name=name,
                    has_pilot_access=has_pilot_access,
                    has_sub_access=has_sub_access,
                    expires_in_days=expires_in_days
                )
                generated_keys.append(access_key)
                
                self.stdout.write(f'✓ Generated key {i+1}: {access_key.key}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to generate key {i+1}: {str(e)}')
                )

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {len(generated_keys)} access key(s)'))
        
        if generated_keys:
            self.stdout.write('\nAccess Key Details:')
            for key in generated_keys:
                access_level = 'Full Access' if key.has_sub_access else 'Pilot Only'
                expiry = key.expires_at.strftime('%Y-%m-%d') if key.expires_at else 'Never'
                
                self.stdout.write(f'  Company: {key.company_name}')
                self.stdout.write(f'  Key: {key.key}')
                self.stdout.write(f'  Access: {access_level}')
                self.stdout.write(f'  Expires: {expiry}')
                self.stdout.write('  ' + '-'*40)