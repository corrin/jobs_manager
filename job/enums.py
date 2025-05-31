from django.db import models
from decimal import Decimal


class JobPricingType(models.TextChoices):
    """
    Define the different types of job pricing calculations
    """
    ESTIMATE = 'estimate', 'Estimate'
    QUOTE = 'quote', 'Quote'
    REALITY = 'reality', 'Reality'


class JobPricingMethodology(models.TextChoices):
    """
    Define the pricing methodology used for a job
    """
    TIME_AND_MATERIALS = 'time_materials', 'Time and Materials'
    FIXED_PRICE = 'fixed_price', 'Fixed Price'


class QuoteStatus(models.TextChoices):
    """
    Status options for quotes
    """
    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent"
    DECLINED = "DECLINED", "Declined"
    ACCEPTED = "ACCEPTED", "Accepted"
    INVOICED = "INVOICED", "Invoiced"
    DELETED = "DELETED", "Deleted"


class InvoiceStatus(models.TextChoices):
    """
    Status options for invoices
    """
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    AUTHORISED = "AUTHORISED", "Authorised"
    DELETED = "DELETED", "Deleted"
    VOIDED = "VOIDED", "Voided"
    PAID = "PAID", "Paid"


class MetalType(models.TextChoices):
    """
    Types of metal used in jobs
    """
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


class RateType(models.TextChoices):
    """
    Types of pay rates for job time entries
    """
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
