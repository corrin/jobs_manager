import uuid
from django.db import models


class Part(models.Model):
    """
    Represents a component or section of a job that contains time entries, 
    material entries, and adjustments.
    
    Each JobPricing can have multiple parts, and each part can have multiple entries.
    For example, a job might have parts like "Fabrication", "Installation", "Finishing", etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(
        "JobPricing",
        on_delete=models.CASCADE,
        related_name="parts",
        null=False,
        blank=False,
    )
    name = models.CharField(max_length=100, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        db_table = "workflow_part"

    def __str__(self):
        job_name = self.job_pricing.job.name if self.job_pricing and self.job_pricing.job else "No Job"
        return f"{self.name} - {job_name}"