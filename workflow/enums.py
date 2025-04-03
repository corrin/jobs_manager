from decimal import Decimal

from django.db import models


class JobPricingType(models.TextChoices):
    FIXED_PRICE = "fixed_price", "Fixed Price"
    TIME_AND_MATERIALS = "time_materials", "Time & Materials"


class JobPricingStage(models.TextChoices):
    ESTIMATE = "estimate", "Estimate"
    QUOTE = "quote", "Quote"
    REALITY = "reality", "Reality"


class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    AUTHORISED = "AUTHORISED", "Authorised"
    DELETED = "DELETED", "Deleted"
    VOIDED = "VOIDED", "Voided"
    PAID = "PAID", "Paid"


class QuoteStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent"
    DECLINED = "DECLINED", "Declined"
    ACCEPTED = "ACCEPTED", "Accepted"
    INVOICED = "INVOICED", "Invoiced"
    DELETED = "DELETED", "Deleted"


class RateType(models.TextChoices):
    ORDINARY = "Ord", "Ordinary Time"
    TIME_AND_HALF = "1.5", "Time and a Half"
    DOUBLE_TIME = "2.0", "Double Time"
    UNPAID = "Unpaid", "Unpaid"

    @property
    def multiplier(self) -> Decimal:
        multipliers = {
            self.ORDINARY: Decimal("1.0"),
            self.TIME_AND_HALF: Decimal("1.5"),
            self.DOUBLE_TIME: Decimal("2.0"),
            self.UNPAID: Decimal("0.0"),
        }
        return multipliers[self]


class MetalType(models.TextChoices):
    STAINLESS_STEEL = "stainless_steel", "Stainless Steel"
    MILD_STEEL = "mild_steel", "Mild Steel"
    ALUMINUM = "aluminum", "Aluminum"
    BRASS = "brass", "Brass"
    COPPER = "copper", "Copper"
    TITANIUM = "titanium", "Titanium"
    ZINC = "zinc", "Zinc"
    GALVANIZED = "galvanized", "Galvanized"
    UNSPECIFIED = "unspecified", "Unspecified"
    OTHER = "other", "Other"
