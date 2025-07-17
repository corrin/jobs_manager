#!/usr/bin/env python
"""Test script to verify the quote chat API endpoint is working properly."""

import logging

import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
# Using the job ID from the original error log
JOB_ID = "523540fd-9c40-463d-a762-594b07012f11"
ENDPOINT = f"{BASE_URL}/job/api/jobs/{JOB_ID}/quote-chat/ai-response/"


def test_with_different_headers():
    """Test the endpoint with different Accept headers to verify 406 error is fixed."""

    test_data = {
        "user_message": "Test message to check if API is working",
        "save_user_message": False,
        "stream": False,
    }

    test_cases = [
        ("No Accept header", {}),
        ("Accept: */*", {"Accept": "*/*"}),
        ("Accept: application/json", {"Accept": "application/json"}),
        ("Accept: text/html", {"Accept": "text/html"}),
        (
            "Accept: text/html,application/json",
            {"Accept": "text/html,application/json"},
        ),
    ]

    logger.info(f"Testing endpoint: {ENDPOINT}\n")

    for test_name, headers in test_cases:
        logger.info(f"Test: {test_name}")
        logger.info(f"Headers: {headers}")

        try:
            response = requests.post(
                ENDPOINT, json=test_data, headers=headers, timeout=10
            )

            logger.info(f"Status Code: {response.status_code}")
            logger.info(
                f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}"
            )

            if response.status_code == 406:
                logger.error("❌ FAILED: Still getting 406 Not Acceptable error")
            elif response.status_code == 200 or response.status_code == 201:
                logger.info("✅ SUCCESS: Request accepted")
            else:
                logger.warning(
                    f"⚠️  Got status code {response.status_code}: {response.text[:100]}..."
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ ERROR: {e}")

        logger.info("-" * 80)
        logger.info("")


def test_options_request():
    """Test OPTIONS request to see CORS handling."""
    logger.info("Testing OPTIONS request:")

    try:
        response = requests.options(ENDPOINT, timeout=10)
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Allow header: {response.headers.get('Allow', 'Not specified')}")
        logger.info(
            f"Content-Type: {response.headers.get('Content-Type', 'Not specified')}"
        )

        if response.status_code == 200:
            logger.info("✅ OPTIONS request successful")
        else:
            logger.warning(f"⚠️  Got status code {response.status_code}")

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ ERROR: {e}")

    logger.info("-" * 80)
    logger.info("")


if __name__ == "__main__":
    logger.info("Testing Quote Chat API Endpoint")
    logger.info("=" * 80)

    # First test OPTIONS
    test_options_request()

    # Then test POST with different headers
    test_with_different_headers()

    logger.info("Note: Make sure the Django server is running on port 8000")
    logger.info("If you're getting connection errors, the server might not be running.")
