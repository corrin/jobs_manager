"""
Google Sheets Service

This module provides functionality for interacting with Google Sheets API.
It handles authentication, reading/writing to spreadsheets, and duplicating spreadsheets.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from workflow.models import CompanyDefaults


logger = logging.getLogger(__name__)

# Scopes required for Google Sheets API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleSheetsService:
    """Service for interacting with Google Sheets API."""

    def __init__(self):
        """Initialize the Google Sheets service."""
        self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.credentials = None
        self.service_account_email = None
        self.sheets_service = None
        self.drive_service = None
        self.authenticated = self._authenticate()

    def _authenticate(self) -> bool:
        """
        Authenticate with Google API using service account credentials.
        
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            
            # Store the service account email for sharing spreadsheets
            self.service_account_email = self.credentials.service_account_email
            
            # Build the services
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            
            logger.info("Successfully authenticated with Google API")
            logger.info(f"Using service account: {self.service_account_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Google API: {str(e)}")
            return False

    def read_spreadsheet(self, spreadsheet_id: str, range_name: str) -> List[List[Any]]:
        """
        Read data from a Google Spreadsheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet to read from.
            range_name: The A1 notation of the range to read.
            
        Returns:
            List of rows, where each row is a list of values.
        """
        if not self.sheets_service:
            # Cutesy and unnecessary check to ensure we have authenticated
            raise Exception("Attempted to read spreadsheet without authentication. Fix the flow.")
        
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()
        
        values = result.get('values', [])
        logger.info(f"Read {len(values)} rows from spreadsheet {spreadsheet_id}")
        return values
        

    def write_to_spreadsheet(
        self, spreadsheet_id: str, range_name: str, values: List[List[Any]]
    ) -> int:
        """
        Write data to a Google Spreadsheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet to write to.
            range_name: The A1 notation of the range to write.
            values: The data to write, as a list of rows.
            
        Returns:
            Number of cells updated.
        """
        
        body = {
            'values': values
        }
        result = self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_name,
            valueInputOption='USER_ENTERED', body=body
        ).execute()
        
        logger.info(f"Updated {result.get('updatedCells')} cells in spreadsheet {spreadsheet_id}")
        return result.get('updatedCells')

    def duplicate_spreadsheet(self, source_spreadsheet_id: str, new_title: str) -> str:
        """
        Duplicate a Google Spreadsheet.
        
        This method creates a full copy of the spreadsheet including all sheets,
        formulas, formatting, and scripts/macros.
        
        Args:
            source_spreadsheet_id: The ID of the spreadsheet to duplicate.
            new_title: The title for the new spreadsheet.
            
        Returns:
            The ID of the newly created spreadsheet.
        """
        
        # Get the original file metadata
        file = self.drive_service.files().get(
            fileId=source_spreadsheet_id, 
            fields='name,parents,mimeType'
        ).execute()
        
        # Create a copy - this preserves all sheets, formulas, formatting, and scripts
        body = {
            'name': new_title,
            'parents': file.get('parents', [])
        }
        
        drive_response = self.drive_service.files().copy(
            fileId=source_spreadsheet_id,
            body=body
        ).execute()
        
        new_spreadsheet_id = drive_response['id']
        logger.info(f"Created new spreadsheet with ID: {new_spreadsheet_id}")
        
        # Set permissions to anyone with the link can edit
        permission = {
            'type': 'anyone',
            'role': 'writer',
            'allowFileDiscovery': False
        }
        
        self.drive_service.permissions().create(
            fileId=new_spreadsheet_id,
            body=permission
        ).execute()
        
        logger.info(f"Set permissions for spreadsheet {new_spreadsheet_id}")
        
        return new_spreadsheet_id
        

    def get_spreadsheet_url(self, spreadsheet_id: str) -> str:
        """
        Get the URL for a Google Spreadsheet.
        
        Args:
            spreadsheet_id: The ID of the spreadsheet.
            
        Returns:
            The URL of the spreadsheet.
        """
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"


def test_connection() -> bool:
    """
    Test the connection to Google Sheets API.
    
    Returns:
        bool: True if connection is successful, False otherwise.
    """
    try:
        service = GoogleSheetsService()
        return service.authenticated
    except Exception as e:
        logger.error(f"Error testing connection to Google Sheets API: {str(e)}")
        return False


def test_read_spreadsheet(spreadsheet_id: str, range_name: str = 'Sheet1!A1:E10') -> List[List[Any]]:
    """
    Test reading from a spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet to read from.
        range_name: The A1 notation of the range to read.
        
    Returns:
        List of rows, where each row is a list of values.
    """
    service = GoogleSheetsService()
    return service.read_spreadsheet(spreadsheet_id, range_name)


def test_write_spreadsheet(
    spreadsheet_id: str, range_name: str = 'Sheet1!A1:B2', values: Optional[List[List[Any]]] = None
) -> int:
    """
    Test writing to a spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet to write to.
        range_name: The A1 notation of the range to write.
        values: The data to write, as a list of rows. Defaults to a test value.
        
    Returns:
        Number of cells updated.
    """
    if values is None:
        values = [
            ['Test', 'Data'],
            ['From', 'API']
        ]
    
    service = GoogleSheetsService()
    return service.write_to_spreadsheet(spreadsheet_id, range_name, values)


def test_duplicate_spreadsheet(source_spreadsheet_id: str, new_title: str = 'Copy of Template') -> str:
    """
    Test duplicating a spreadsheet.
    
    Args:
        source_spreadsheet_id: The ID of the spreadsheet to duplicate.
        new_title: The title for the new spreadsheet.
        
    Returns:
        The ID of the newly created spreadsheet.
    """
    service = GoogleSheetsService()
    new_id = service.duplicate_spreadsheet(source_spreadsheet_id, new_title)
    return new_id


def create_quote_from_template(job_number: int, client_name: str) -> str:
    """
    Create a new quote spreadsheet from the master template.
    
    Args:
        job_number: The job number to include in the title.
        client_name: The client name to include in the title.
        
    Returns:
        The URL of the newly created spreadsheet.
    """
    
    # Get the master template URL from CompanyDefaults
    company_defaults = CompanyDefaults.get_instance()
    template_url = company_defaults.master_quote_template_url
    
    if not template_url:
        raise ValueError("Master quote template URL not set in Company Defaults")
    
    # Extract the spreadsheet ID from the URL
    # URL format: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit
    template_id = template_url.split('/d/')[1].split('/')[0]
    
    # Create a new title for the quote
    new_title = f"Quote for Job {job_number} - {client_name}"
    
    # Duplicate the template
    service = GoogleSheetsService()
    new_spreadsheet_id = service.duplicate_spreadsheet(template_id, new_title)
    
    # Return the URL of the new spreadsheet
    return service.get_spreadsheet_url(new_spreadsheet_id)