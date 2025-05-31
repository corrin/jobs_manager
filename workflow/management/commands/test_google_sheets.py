from django.core.management.base import BaseCommand
from django.utils import timezone

from workflow.services.google_sheets_service import (
    test_connection,
    test_read_spreadsheet,
    test_write_spreadsheet,
    test_duplicate_spreadsheet,
)
from workflow.models import CompanyDefaults


class Command(BaseCommand):
    help = 'Test Google Sheets API integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--read-only',
            action='store_true',
            help='Only test reading from the spreadsheet, skip write and duplicate tests',
        )

    def handle(self, *args, **options):
        read_only = options.get('read_only', False)
        
        self.stdout.write("Testing Google Sheets API integration...")
        
        # Test connection
        self.stdout.write("\n1. Testing connection to Google Sheets API...")
        if test_connection():
            self.stdout.write(self.style.SUCCESS("✅ Connection successful!"))
        else:
            self.stdout.write(
                self.style.ERROR("❌ Connection failed. Check your GOOGLE_CREDENTIALS_PATH in .env file.")
            )
            return
        
        # Get template URL from CompanyDefaults
        company_defaults = CompanyDefaults.get_instance()
        template_url = company_defaults.master_quote_template_url
        
        if not template_url:
            self.stdout.write(
                self.style.ERROR("\n❌ Master quote template URL not set in Company Defaults.")
            )
            self.stdout.write("Please set it in the admin interface before continuing.")
            return
        
        # Extract spreadsheet ID from URL
        try:
            spreadsheet_id = template_url.split('/d/')[1].split('/')[0]
            self.stdout.write(f"\nUsing spreadsheet ID: {spreadsheet_id}")
        except (IndexError, AttributeError):
            self.stdout.write(
                self.style.ERROR(
                    "\n❌ Invalid template URL format. Expected format: "
                    "https://docs.google.com/spreadsheets/d/{id}/edit"
                )
            )
            return
        
        # Test reading from spreadsheet
        self.stdout.write("\n2. Testing reading from spreadsheet...")
        try:
            values = test_read_spreadsheet(spreadsheet_id, 'Primary Details!A1:B5')
            self.stdout.write(
                self.style.SUCCESS(f"✅ Successfully read {len(values)} rows from spreadsheet:")
            )
            for row in values[:5]:  # Show first 5 rows
                self.stdout.write(f"  {row}")
            if len(values) > 5:
                self.stdout.write(f"  ... and {len(values) - 5} more rows")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error reading spreadsheet: {str(e)}"))
            return
        
        if read_only:
            self.stdout.write(self.style.SUCCESS("\n✅ Read-only tests passed successfully!"))
            return
        
        # Test writing to spreadsheet
        self.stdout.write("\n3. Testing writing to spreadsheet...")
        try:
            test_data = [
                ['Test', 'Data'],
                ['From', 'API'],
                ['Timestamp', str(timezone.now())]
            ]
            cells_updated = test_write_spreadsheet(spreadsheet_id, 'Primary Details!A20:B22', test_data)
            self.stdout.write(
                self.style.SUCCESS(f"✅ Successfully updated {cells_updated} cells in spreadsheet")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error writing to spreadsheet: {str(e)}"))
            return
        
        # Test duplicating spreadsheet
        self.stdout.write("\n4. Testing duplicating spreadsheet...")
        try:
            new_title = f"Test Copy - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            new_id = test_duplicate_spreadsheet(spreadsheet_id, new_title)
            self.stdout.write(
                self.style.SUCCESS(f"✅ Successfully created new spreadsheet with ID: {new_id}")
            )
            self.stdout.write(f"   URL: https://docs.google.com/spreadsheets/d/{new_id}/edit")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error duplicating spreadsheet: {str(e)}"))
            return
        
        self.stdout.write(self.style.SUCCESS("\n✅ All tests passed successfully!"))