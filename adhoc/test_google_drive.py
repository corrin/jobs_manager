#!/usr/bin/env python3
"""
Test script to verify Google Drive API access and folder permissions.
"""

import os
import sys

import django
from googleapiclient.discovery import build

# Setup Django
sys.path.append("/home/corrin/src/jobs_manager")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings.local")
django.setup()

from apps.job.importers.google_sheets import _get_credentials


def test_google_drive_access() -> bool:
    """Test Google Drive API access and folder operations."""

    try:
        # Get credentials
        print("🔐 Getting Google API credentials...")
        creds = _get_credentials()
        print("✅ Credentials loaded successfully")

        # Build Drive service
        print("\n🔨 Building Google Drive service...")
        drive_service = build("drive", "v3", credentials=creds)
        print("✅ Drive service created successfully")

        # Test folder access
        folder_id = "1DNw8rOVNaqRuDB56yR3e4dSHxTmXGQJu"
        print(f"\n📁 Testing access to folder: {folder_id}")

        # Get folder metadata (with Shared Drive support)
        folder = (
            drive_service.files()
            .get(fileId=folder_id, supportsAllDrives=True)
            .execute()
        )
        print(f"✅ Folder found: {folder['name']}")
        print(
            f"   Owner: {folder.get('owners', [{}])[0].get('displayName', 'Unknown')}"
        )
        print(f"   Created: {folder.get('createdTime', 'Unknown')}")

        # List folder contents (with Shared Drive support)
        print("\n📋 Listing contents of folder...")
        results = (
            drive_service.files()
            .list(
                q=f"'{folder_id}' in parents",
                fields="files(id, name, mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        files = results.get("files", [])
        if files:
            print(f"✅ Found {len(files)} items:")
            for file in files:
                print(f"   - {file['name']} ({file['mimeType']})")
        else:
            print("✅ Folder is empty (as expected)")

        print("\n🎉 All tests passed! Google Drive integration is working correctly.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"   Type: {type(e).__name__}")

        # More detailed error info
        if hasattr(e, "resp"):
            print(f"   HTTP Status: {e.resp.status}")
            print(f"   HTTP Reason: {e.resp.reason}")

        return False

    return True


if __name__ == "__main__":
    success = test_google_drive_access()
    sys.exit(0 if success else 1)
