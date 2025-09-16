import logging
import os
import sys

import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from apps.workflow.models import AIProvider

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Get all AI providers
all_providers = AIProvider.objects.all()
logger.info("All AI Providers:")
for provider in all_providers:
    logger.info(
        f"ID: {provider.id}, Name: {provider.name}, Type: {provider.provider_type}, Default: {provider.default}"
    )

# Get a specific AI provider by type (e.g., 'Claude' or 'Gemini')
# Replace 'Claude' with the actual provider_type you are looking for
claude_provider = AIProvider.objects.filter(provider_type="Claude").first()
if claude_provider:
    logger.info("Claude AI Provider Details:")
    logger.info(
        f"ID: {claude_provider.id}, Name: {claude_provider.name}, Type: {claude_provider.provider_type}, Default: {claude_provider.default}"
    )
else:
    logger.info("No Claude AI provider found.")

# You can also check for 'Gemini' or other types
gemini_provider = AIProvider.objects.filter(provider_type="Gemini").first()
if gemini_provider:
    logger.info("Gemini AI Provider Details:")
    logger.info(
        f"ID: {gemini_provider.id}, Name: {gemini_provider.name}, Type: {gemini_provider.provider_type}, Default: {gemini_provider.default}"
    )
else:
    logger.info("No Gemini AI provider found.")
