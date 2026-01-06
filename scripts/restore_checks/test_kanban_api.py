#!/usr/bin/env python
"""Test the Kanban API endpoint to verify it's working correctly."""

import json
import sys
import urllib.error
import urllib.request


def test_kanban_api(host_port: str = "localhost:8000") -> bool:
    """Test the Kanban API endpoint.

    Returns True if successful, False otherwise.
    """
    url = f"http://{host_port}/job/api/jobs/fetch-all/"

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
    except urllib.error.URLError as e:
        print(f"✗ ERROR: Cannot connect to server at {host_port}")
        print(f"  {e}")
        return False
    except json.JSONDecodeError as e:
        print("✗ ERROR: Invalid JSON response")
        print(f"  {e}")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

    # Check API response structure
    if not data.get("success"):
        print("✗ ERROR: API returned success=false")
        if "error" in data:
            print(f"  Error: {data['error']}")
        return False

    active_jobs = data.get("active_jobs", [])
    archived_count = data.get("total_archived", len(data.get("archived_jobs", [])))

    if len(active_jobs) == 0:
        print("✗ ERROR: API returned no active jobs")
        return False

    print(f"✓ API working: {len(active_jobs)} active jobs, {archived_count} archived")
    return True


if __name__ == "__main__":
    host_port = sys.argv[1] if len(sys.argv) > 1 else "localhost:8000"
    print(f"Testing Kanban API at {host_port}...")
    success = test_kanban_api(host_port)
    sys.exit(0 if success else 1)
