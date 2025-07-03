#!/usr/bin/env python
"""Test script to verify the quote chat API endpoint is working properly."""

import requests
import json
import sys

# Test configuration
BASE_URL = "http://localhost:8000"
JOB_ID = "523540fd-9c40-463d-a762-594b07012f11"  # Using the job ID from the original error log
ENDPOINT = f"{BASE_URL}/job/api/jobs/{JOB_ID}/quote-chat/ai-response/"

def test_with_different_headers():
    """Test the endpoint with different Accept headers to verify 406 error is fixed."""
    
    test_data = {
        "user_message": "Test message to check if API is working",
        "save_user_message": False,
        "stream": False
    }
    
    test_cases = [
        ("No Accept header", {}),
        ("Accept: */*", {"Accept": "*/*"}),
        ("Accept: application/json", {"Accept": "application/json"}),
        ("Accept: text/html", {"Accept": "text/html"}),
        ("Accept: text/html,application/json", {"Accept": "text/html,application/json"}),
    ]
    
    print(f"Testing endpoint: {ENDPOINT}\n")
    
    for test_name, headers in test_cases:
        print(f"Test: {test_name}")
        print(f"Headers: {headers}")
        
        try:
            response = requests.post(
                ENDPOINT,
                json=test_data,
                headers=headers,
                timeout=10
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
            
            if response.status_code == 406:
                print("❌ FAILED: Still getting 406 Not Acceptable error")
            elif response.status_code == 200 or response.status_code == 201:
                print("✅ SUCCESS: Request accepted")
            else:
                print(f"⚠️  Got status code {response.status_code}: {response.text[:100]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR: {e}")
            
        print("-" * 80)
        print()

def test_options_request():
    """Test OPTIONS request to see CORS handling."""
    print("Testing OPTIONS request:")
    
    try:
        response = requests.options(ENDPOINT, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Allow header: {response.headers.get('Allow', 'Not specified')}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}")
        
        if response.status_code == 200:
            print("✅ OPTIONS request successful")
        else:
            print(f"⚠️  Got status code {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: {e}")
        
    print("-" * 80)
    print()

if __name__ == "__main__":
    print("Testing Quote Chat API Endpoint")
    print("=" * 80)
    
    # First test OPTIONS
    test_options_request()
    
    # Then test POST with different headers
    test_with_different_headers()
    
    print("\nNote: Make sure the Django server is running on port 8000")
    print("If you're getting connection errors, the server might not be running.")