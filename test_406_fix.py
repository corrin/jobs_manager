#!/usr/bin/env python
"""
Simple test to check if the 406 error is fixed by checking the view's renderer configuration.
"""

import logging
import os
import sys

import django

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from rest_framework.renderers import BrowsableAPIRenderer, JSONRenderer

from apps.job.views.job_quote_chat_views import JobQuoteChatAIResponseView


def check_renderer_configuration():
    """Check if the view has the correct renderer classes configured."""

    logger.info("Checking JobQuoteChatAIResponseView renderer configuration...")
    logger.info("-" * 60)

    # Get the renderer classes
    renderer_classes = JobQuoteChatAIResponseView.renderer_classes

    logger.info(f"Configured renderer classes: {renderer_classes}")
    logger.info(f"Number of renderers: {len(renderer_classes)}")

    # Check each renderer
    has_json = False
    has_browsable = False

    for renderer in renderer_classes:
        logger.info(f"  - {renderer.__name__}")
        if renderer == JSONRenderer:
            has_json = True
        elif renderer == BrowsableAPIRenderer:
            has_browsable = True

    logger.info("-" * 60)

    if has_json and has_browsable:
        logger.info(
            "✅ SUCCESS: Both JSONRenderer and BrowsableAPIRenderer are configured!"
        )
        logger.info("   The 406 error should be fixed after restarting the server.")
        return True
    else:
        logger.error("❌ FAILED: Missing renderers:")
        if not has_json:
            logger.error("   - JSONRenderer is missing")
        if not has_browsable:
            logger.error("   - BrowsableAPIRenderer is missing")
        return False


def check_rest_framework_settings():
    """Check the REST_FRAMEWORK settings."""
    from django.conf import settings

    logger.info("\nChecking REST_FRAMEWORK settings...")
    logger.info("-" * 60)

    if hasattr(settings, "REST_FRAMEWORK"):
        rf_settings = settings.REST_FRAMEWORK

        if "DEFAULT_RENDERER_CLASSES" in rf_settings:
            logger.info(
                f"DEFAULT_RENDERER_CLASSES: {rf_settings['DEFAULT_RENDERER_CLASSES']}"
            )
        else:
            logger.info("DEFAULT_RENDERER_CLASSES: Not configured")

        if "DEFAULT_AUTHENTICATION_CLASSES" in rf_settings:
            logger.info(
                f"DEFAULT_AUTHENTICATION_CLASSES: {rf_settings['DEFAULT_AUTHENTICATION_CLASSES']}"
            )
    else:
        logger.error("REST_FRAMEWORK settings not found!")


if __name__ == "__main__":
    logger.info("Testing 406 Error Fix")
    logger.info("=" * 60)

    # Check renderer configuration
    renderer_ok = check_renderer_configuration()

    # Check REST framework settings
    check_rest_framework_settings()

    logger.info("\n" + "=" * 60)
    if renderer_ok:
        logger.info("✅ The code changes are correct!")
        logger.warning(
            "⚠️  Remember to restart the Django server for changes to take effect."
        )
    else:
        logger.error("❌ The renderer configuration needs to be fixed.")
