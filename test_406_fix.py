#!/usr/bin/env python
"""
Simple test to check if the 406 error is fixed by checking the view's renderer configuration.
"""

import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer

from apps.job.views.job_quote_chat_views import JobQuoteChatAIResponseView


def check_renderer_configuration():
    """Check if the view has the correct renderer classes configured."""

    print("Checking JobQuoteChatAIResponseView renderer configuration...")
    print("-" * 60)

    # Get the renderer classes
    renderer_classes = JobQuoteChatAIResponseView.renderer_classes

    print(f"Configured renderer classes: {renderer_classes}")
    print(f"Number of renderers: {len(renderer_classes)}")

    # Check each renderer
    has_json = False
    has_browsable = False

    for renderer in renderer_classes:
        print(f"  - {renderer.__name__}")
        if renderer == JSONRenderer:
            has_json = True
        elif renderer == BrowsableAPIRenderer:
            has_browsable = True

    print("-" * 60)

    if has_json and has_browsable:
        print("✅ SUCCESS: Both JSONRenderer and BrowsableAPIRenderer are configured!")
        print("   The 406 error should be fixed after restarting the server.")
        return True
    else:
        print("❌ FAILED: Missing renderers:")
        if not has_json:
            print("   - JSONRenderer is missing")
        if not has_browsable:
            print("   - BrowsableAPIRenderer is missing")
        return False


def check_rest_framework_settings():
    """Check the REST_FRAMEWORK settings."""
    from django.conf import settings

    print("\nChecking REST_FRAMEWORK settings...")
    print("-" * 60)

    if hasattr(settings, "REST_FRAMEWORK"):
        rf_settings = settings.REST_FRAMEWORK

        if "DEFAULT_RENDERER_CLASSES" in rf_settings:
            print(
                f"DEFAULT_RENDERER_CLASSES: {rf_settings['DEFAULT_RENDERER_CLASSES']}"
            )
        else:
            print("DEFAULT_RENDERER_CLASSES: Not configured")

        if "DEFAULT_AUTHENTICATION_CLASSES" in rf_settings:
            print(
                f"DEFAULT_AUTHENTICATION_CLASSES: {rf_settings['DEFAULT_AUTHENTICATION_CLASSES']}"
            )
    else:
        print("REST_FRAMEWORK settings not found!")


if __name__ == "__main__":
    print("Testing 406 Error Fix")
    print("=" * 60)

    # Check renderer configuration
    renderer_ok = check_renderer_configuration()

    # Check REST framework settings
    check_rest_framework_settings()

    print("\n" + "=" * 60)
    if renderer_ok:
        print("✅ The code changes are correct!")
        print("⚠️  Remember to restart the Django server for changes to take effect.")
    else:
        print("❌ The renderer configuration needs to be fixed.")
