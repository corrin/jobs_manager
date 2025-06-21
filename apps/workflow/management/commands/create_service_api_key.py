from django.core.management.base import BaseCommand
from apps.workflow.models import ServiceAPIKey


class Command(BaseCommand):
    help = 'Create a service API key for MCP access'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            default='Chatbot Service',
            help='Name for the service API key'
        )

    def handle(self, *args, **options):
        name = options['name']
        
        # Check if a key with this name already exists
        existing_key = ServiceAPIKey.objects.filter(name=name).first()
        if existing_key:
            self.stdout.write(
                self.style.WARNING(f'API key "{name}" already exists: {existing_key.key}')
            )
            return
        
        # Create new API key
        service_key = ServiceAPIKey.objects.create(name=name)
        
        self.stdout.write(
            self.style.SUCCESS(f'Created API key "{name}": {service_key.key}')
        )
        self.stdout.write(
            self.style.WARNING('Save this key securely - it cannot be retrieved again!')
        )