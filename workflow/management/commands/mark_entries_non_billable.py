from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from timesheet.models import TimeEntry
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Marks all Shop jobs time entries as non-billable (sets is_billable=False)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            dest='limit',
            help='Limit the number of entries to update (for testing)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            help='Skip confirmation and proceed with update',
        )

    def handle(self, *args, **options):
        # Get options
        limit = options.get('limit')
        force = options.get('force', False)
        
        # Find all billable Shop job entries
        entries_query = TimeEntry.objects.filter(
            is_billable=True,
            job_pricing__job__client__name='MSM (Shop)'
        )
        
        # Apply limit if specified
        if limit:
            entries_query = entries_query.order_by('-id')[:limit]
        
        # Count entries to update
        count = entries_query.count()
        
        # Exit if no entries found
        if count == 0:
            self.stdout.write(
                self.style.WARNING('No billable Shop job entries found to update.')
            )
            return
        
        # Confirm the action unless --force is used
        if not force:
            message = f"You are about to mark {count} Shop job entries as non-billable."
            message += f"\nAre you sure you want to continue? [y/N]: "
            
            if input(message).lower() != 'y':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return
        
        # Perform the update inside a transaction
        try:
            with transaction.atomic():
                updated = entries_query.update(is_billable=False)
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully marked {updated} Shop job entries as non-billable')
                )
                logger.info(f'Marked {updated} Shop job entries as non-billable')
                
        except Exception as e:
            logger.error(f'Error updating Shop job entries: {str(e)}')
            raise CommandError(f'Failed to update Shop job entries: {str(e)}')
