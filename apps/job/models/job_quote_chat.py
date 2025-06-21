import uuid
from django.db import models
from .job import Job


class JobQuoteChat(models.Model):
    """
    Stores chat messages for the interactive quoting feature linked to jobs.
    Each job can have an associated chat conversation where users interact 
    with an LLM to generate quotes.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        Job, 
        on_delete=models.CASCADE, 
        related_name='quote_chat_messages'
    )
    message_id = models.CharField(
        max_length=100, 
        unique=True, 
        help_text="Frontend-generated unique ID"
    )
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Extra data like streaming status, processing time, etc."
    )
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['job', 'timestamp']),
            models.Index(fields=['message_id']),
        ]
        db_table = 'job_quote_chat'
    
    def __str__(self):
        return f"{self.job.name} - {self.role}: {self.content[:50]}..."