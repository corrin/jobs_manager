from django.db import models


class AIProviderTypes(models.TextChoices):
    ANTHROPIC = "Claude"
    GOOGLE = "Gemini"
    MISTRAL = "Mistral"
