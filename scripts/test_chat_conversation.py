#!/usr/bin/env python
"""
Test script for quote chat conversation without frontend.
Run with: python test_chat_conversation.py
"""

import os

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from apps.job.models import Job, JobQuoteChat
from apps.job.services.gemini_chat_service import GeminiChatService


def test_conversation():
    """Test a multi-turn conversation with context preservation."""

    # Get a job to test with
    job = Job.objects.first()
    if not job:
        print("No jobs found in database. Please create a job first.")
        return

    print(f"Testing with job: {job.job_number} - {job.name}")
    print("=" * 60)

    # Clear any existing chat for clean test
    deleted = JobQuoteChat.objects.filter(job=job).delete()
    print(f"Cleared {deleted[0]} existing chat messages")

    # Initialize the service
    service = GeminiChatService()

    # Test conversations
    test_messages = [
        {
            "content": "3 stainless steel boxes, 700×700×400mm, welded seams",
            "expected_mode": "CALC",
            "description": "Initial request - should trigger CALC mode",
        },
        {
            "content": "0.8mm 304 stainless, open top",
            "expected_mode": "CALC",
            "description": "Follow-up with more details - should remember context",
        },
        {
            "content": "Good. Let's price it",
            "expected_mode": "PRICE",
            "description": "Request pricing - should trigger PRICE mode with context",
        },
    ]

    for i, test in enumerate(test_messages, 1):
        print(f"\n{'=' * 60}")
        print(f"TEST {i}: {test['description']}")
        print(f"Expected mode: {test['expected_mode']}")
        print(f"{'=' * 60}")
        print(f"User: {test['content']}")
        print("-" * 40)

        try:
            # Save user message to database
            user_msg = JobQuoteChat.objects.create(
                job=job,
                message_id=f"user-test-{i}",
                role="user",
                content=test["content"],
            )

            # Generate AI response
            response = service.generate_mode_response(
                job_id=str(job.id),
                user_message=test["content"],
                mode=None,  # Let it infer the mode
            )

            # Display response
            print(f"Assistant response (first 500 chars):")
            print(response.content[:500])
            if len(response.content) > 500:
                print(f"... (truncated, total length: {len(response.content)} chars)")

            # Check if response contains expected elements
            if test["expected_mode"] == "CALC":
                if (
                    "items" in response.content.lower()
                    or "calculated" in response.content.lower()
                ):
                    print("✓ Response appears to contain calculations")
            elif test["expected_mode"] == "PRICE":
                if (
                    "option" in response.content.lower()
                    or "price" in response.content.lower()
                ):
                    print("✓ Response appears to contain pricing")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()

    # Show final chat history
    print(f"\n{'=' * 60}")
    print("FINAL CHAT HISTORY IN DATABASE")
    print("=" * 60)
    messages = JobQuoteChat.objects.filter(job=job).order_by("timestamp")
    for msg in messages:
        role = "User" if msg.role == "user" else "AI"
        print(f"{role}: {msg.content[:100]}...")
        if len(msg.content) > 100:
            print(f"      ... (truncated from {len(msg.content)} chars)")

    print(f"\nTotal messages in conversation: {messages.count()}")
    print("\nTest complete!")


if __name__ == "__main__":
    test_conversation()
