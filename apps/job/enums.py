from django.db import models


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
