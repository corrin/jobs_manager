from decimal import Decimal

# Re-export job-related enums from job.enums for backward compatibility
from job.enums import (
    JobPricingType,
    JobPricingType,
    InvoiceStatus,
    QuoteStatus,
    RateType,
    MetalType,
)

from django.db import models


class AIProviderTypes(models.TextChoices):
    ANTHROPIC = "Claude"
    GOOGLE = "Gemini"
