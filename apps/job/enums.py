from django.db import models


class JobPricingStage(models.TextChoices):
    """
    Define the different stages of job pricing calculations
    """

    ESTIMATE = "estimate", "Estimate"
    QUOTE = "quote", "Quote"
    REALITY = "reality", "Reality"


class JobPricingMethodology(models.TextChoices):
    """
    Define the pricing methodology used for a job
    """

    TIME_AND_MATERIALS = "time_materials", "Time and Materials"
    FIXED_PRICE = "fixed_price", "Fixed Price"


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
