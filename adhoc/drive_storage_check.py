#!/usr/bin/env python3
"""
Check Google Drive storage usage for service account.
"""

import logging
import os

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def check_drive_storage():
    """Check Google Drive storage usage and list files by size."""

    # Get credentials
    key_file = os.getenv("GCP_CREDENTIALS")
    if not key_file or not os.path.exists(key_file):
        logger.error(f"Credentials file not found: {key_file}")
        return False

    logger.info(f"Loading credentials from: {key_file}")

    try:
        # Load credentials
        creds = service_account.Credentials.from_service_account_file(
            key_file, scopes=SCOPES
        )
        logger.info(f"Service account: {creds.service_account_email}")

        # Build Drive service
        drive_service = build("drive", "v3", credentials=creds)

        # Get storage quota information
        logger.info(f"Checking storage quota...")
        try:
            about = drive_service.about().get(fields="storageQuota,user").execute()

            if "storageQuota" in about:
                quota = about["storageQuota"]

                # Convert bytes to GB for readability
                def bytes_to_gb(bytes_val):
                    if bytes_val:
                        return round(int(bytes_val) / (1024**3), 2)
                    return 0

                limit = bytes_to_gb(quota.get("limit"))
                usage = bytes_to_gb(quota.get("usage"))
                drive_usage = bytes_to_gb(quota.get("usageInDrive"))

                logger.info(f"Storage Usage:")
                logger.info(f"   Total Used: {usage} GB")
                logger.info(f"   Drive Used: {drive_usage} GB")
                logger.info(f"   Limit: {limit} GB" if limit else "   Limit: Unlimited")

                if limit:
                    percentage = round((usage / limit) * 100, 1)
                    logger.info(f"   Usage: {percentage}%")

                    if percentage > 95:
                        logger.error("CRITICAL: Storage almost full!")
                    elif percentage > 80:
                        logger.warning("WARNING: Storage getting full")
                    else:
                        logger.info("Storage OK")
            else:
                logger.info("ℹStorage quota information not available")

        except Exception as e:
            logger.error(f"Could not get storage info: {e}")

        # List files by size to find large ones
        logger.info(f"Finding largest files...")
        try:
            results = (
                drive_service.files()
                .list(
                    pageSize=50,
                    fields="files(id, name, size, mimeType, createdTime)",
                    orderBy="quotaBytesUsed desc",
                )
                .execute()
            )

            files = results.get("files", [])

            logger.info(f"   Top {min(15, len(files))} largest files:")

            total_size = 0
            for i, file in enumerate(files[:15]):
                size = int(file.get("size", 0)) if file.get("size") else 0
                total_size += size
                size_mb = round(size / (1024 * 1024), 2) if size > 0 else 0
                created = file.get("createdTime", "Unknown")[:10]  # Just date

                # Truncate long names
                name = file["name"]
                if len(name) > 40:
                    name = name[:37] + "..."

                logger.info(f"   {i+1:2}. {name:40} {size_mb:8.2f} MB  {created}")

            total_mb = round(total_size / (1024 * 1024), 2)
            logger.info(f"  Top 15 files total: {total_mb} MB")

        except Exception as e:
            logger.error(f"  Could not list files: {e}")

        # Count files by type
        logger.info(f"  File type breakdown...")
        try:
            all_results = (
                drive_service.files()
                .list(pageSize=1000, fields="files(mimeType)")
                .execute()
            )

            all_files = all_results.get("files", [])
            type_counts = {}

            for file in all_files:
                mime_type = file.get("mimeType", "unknown")
                # Simplify mime types for readability
                if "folder" in mime_type:
                    file_type = "Folders"
                elif "spreadsheet" in mime_type:
                    file_type = "Spreadsheets"
                elif "document" in mime_type:
                    file_type = "Documents"
                elif "presentation" in mime_type:
                    file_type = "Presentations"
                else:
                    file_type = "Other"

                type_counts[file_type] = type_counts.get(file_type, 0) + 1

            logger.info(f"  File counts by type:")
            for file_type, count in sorted(type_counts.items()):
                logger.info(f"   {file_type:15}: {count:4} files")

            logger.info(f" Total files: {len(all_files)}")

        except Exception as e:
            logger.error(f"  Could not count file types: {e}")

        return True

    except Exception as e:
        logger.error(f"  ERROR: {e}")
        return False


if __name__ == "__main__":
    check_drive_storage()
