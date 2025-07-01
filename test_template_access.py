#!/usr/bin/env python3
"""
Test access to the quote template spreadsheet.
"""

import os

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def test_template_access():
    """Test access to the quote template."""

    # Get credentials
    key_file = os.getenv("GCP_CREDENTIALS")
    creds = service_account.Credentials.from_service_account_file(
        key_file, scopes=SCOPES
    )
    drive_service = build("drive", "v3", credentials=creds)

    # Template from CompanyDefaults
    template_url = "https://docs.google.com/spreadsheets/d/1EAnvpV-pZwYPPKfpFPTd60DsOhFk9oClNtx6HLvJtSI/edit?gid=0#gid=0"
    template_id = "1EAnvpV-pZwYPPKfpFPTd60DsOhFk9oClNtx6HLvJtSI"

    print(f"🔍 Testing template access: {template_id}")

    try:
        # Try to get template file info
        template_info = drive_service.files().get(fileId=template_id).execute()
        print(f"✅ Template accessible: '{template_info['name']}'")
        print(
            f"   Owner: {template_info.get('owners', [{}])[0].get('displayName', 'Unknown')}"
        )
        print(f"   Size: {template_info.get('size', 'Unknown')} bytes")

        # Try to copy the template to test the operation
        print(f"\n🔨 Testing template copy operation...")

        copy_metadata = {
            "name": "Test Copy - DELETE ME",
            "parents": [
                "1GggflKB5yYbXQxIWOUokDbWa6usTrzhk"
            ],  # Jobs Manager folder we created
        }

        copied_file = (
            drive_service.files().copy(fileId=template_id, body=copy_metadata).execute()
        )

        print(f"✅ Template copy successful: {copied_file['id']}")

        # Clean up test copy
        drive_service.files().delete(fileId=copied_file["id"]).execute()
        print("🧹 Test copy deleted")

        return True

    except Exception as e:
        print(f"❌ Template test failed: {e}")
        if hasattr(e, "resp"):
            print(f"   HTTP Status: {e.resp.status}")
            print(f"   HTTP Reason: {e.resp.reason}")
        return False


if __name__ == "__main__":
    test_template_access()
