import abc
import logging
from typing import Any, Dict, Optional, Tuple

from apps.workflow.enums import AIProviderTypes
from apps.workflow.helpers import get_company_defaults

# from .providers.gemini_provider import GeminiPriceExtractionProvider
# from .providers.claude_provider import ClaudePriceExtractionProvider
from .providers.mistral_provider import MistralPriceExtractionProvider

logger = logging.getLogger(__name__)


class PriceExtractionProvider(abc.ABC):
    """Abstract base class for AI price extraction providers."""

    @abc.abstractmethod
    def extract_price_data(
        self, file_path: str, content_type: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract price data from a supplier price list file.

        Args:
            file_path: Path to the price list file
            content_type: MIME type of the file

        Returns:
            Tuple containing extracted data dict and error message if any
        """

    @abc.abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider."""


class PriceExtractionFactory:
    """Factory for creating AI price extraction providers."""

    @staticmethod
    def create_provider(provider_type: str, api_key: str) -> PriceExtractionProvider:
        """Create a provider instance based on type."""
        if provider_type == AIProviderTypes.MISTRAL:
            return MistralPriceExtractionProvider(api_key)
        #       elif provider_type == AIProviderTypes.GOOGLE:
        #            return GeminiPriceExtractionProvider(api_key)
        #        elif provider_type == AIProviderTypes.ANTHROPIC:
        #            return ClaudePriceExtractionProvider(api_key)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")


def get_prioritized_active_providers():
    """
    Get all active AI providers sorted by priority.
    Priority order: Mistral > Claude > Gemini
    """
    company_defaults = get_company_defaults()
    active_providers = company_defaults.ai_providers.filter(
        default=True, api_key__isnull=False
    ).exclude(api_key="")

    # Define priority order (lower number = higher priority)
    priority_map = {
        AIProviderTypes.MISTRAL: 1,
        #        AIProviderTypes.ANTHROPIC: 3,  # Claude
        AIProviderTypes.GOOGLE: 2,  # Gemini
    }

    # Sort by priority
    sorted_providers = sorted(
        active_providers, key=lambda p: priority_map.get(p.provider_type, 999)
    )

    return sorted_providers


def extract_price_data(
    file_path: str, content_type: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Price extraction function that uses the highest priority active AI provider.

    Args:
        file_path: Path to the price list file
        content_type: MIME type of the file

    Returns:
        Tuple containing extracted data dict and error message if any
    """
    # 1. Get all active providers
    prioritized_providers = get_prioritized_active_providers()

    if not prioritized_providers:
        return (
            None,
            "No active AI providers configured with API keys. Please configure one in company settings.",
        )

    # 2. Use the top priority provider (Mistral first)
    ai_provider = prioritized_providers[0]

    # 3. Create provider instance and call - fail early, don't eat errors
    provider = PriceExtractionFactory.create_provider(
        ai_provider.provider_type, ai_provider.api_key
    )

    logger.info(f"Using {provider.get_provider_name()} for price extraction")
    return provider.extract_price_data(file_path, content_type)
