#!/usr/bin/env python
"""
Generate a curl command to reproduce the Xero Projects API error.
"""

import os
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobs_manager.settings')
django.setup()

from apps.workflow.models import XeroToken
from apps.client.models import Client

def main():
    # Get current token
    token = XeroToken.objects.first()
    if not token:
        print("No Xero token found")
        return

    tenant_id = token.tenant_id
    access_token = token.access_token

    # Look up City Limousines contact
    contact_name = "City Limousines"
    client = Client.objects.filter(name__icontains=contact_name).first()

    if not client:
        print(f"Client '{contact_name}' not found in database")
        return

    if not client.xero_contact_id:
        print(f"Client '{client.name}' has no xero_contact_id")
        return

    print(f"Found client: {client.name}")
    print(f"Contact ID: {client.xero_contact_id}")
    print(f"Archived: {client.xero_archived}")
    print(f"Last synced: {client.xero_last_synced}")

    # Test with this contact
    payload = {
        "contactId": client.xero_contact_id,
        "name": f"Test Project for {client.name}"
    }

    # Generate curl command
    curl_command = f"""curl -X POST 'https://api.xero.com/projects.xro/2.0/Projects' \\
  -H 'Authorization: Bearer {access_token}' \\
  -H 'Xero-Tenant-Id: {tenant_id}' \\
  -H 'Content-Type: application/json' \\
  -d '{json.dumps(payload)}'"""

    print("Curl command:")
    print(curl_command)

    print(f"\nToken expires at: {token.expires_at}")
    print(f"Current time: {datetime.now()}")

    print("\n=== Running curl command ===")
    import subprocess
    result = subprocess.run(curl_command, shell=True, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")

if __name__ == "__main__":
    main()
