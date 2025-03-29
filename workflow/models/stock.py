from decimal import Decimal
from django.db import models
from django.utils import timezone
import logging

from workflow.models.job import Job

logger = logging.getLogger(__name__)

class Stock(models.Model):
    """
    Model for tracking inventory items.
    Each stock item represents a quantity of material that can be assigned to jobs.

    EARLY DRAFT: REVIEW AND TEST
    """
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_items',
        help_text="The job this stock item is assigned to"
    )
    
    description = models.CharField(
        max_length=255,
        help_text="Description of the stock item"
    )
    
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Current quantity of the stock item"
    )
    
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Cost per unit of the stock item"
    )
    
    date = models.DateTimeField(
        default=timezone.now,
        help_text="Date the stock item was created"
    )
    
    source = models.CharField(
        max_length=50,
        choices=[
            ('purchase_order', 'Purchase Order'),
            ('split', 'Split from another stock item'),
            ('manual', 'Manual Entry'),
        ],
        help_text="Source of the stock item"
    )
    
    source_id = models.CharField(
        max_length=100,
        help_text="ID of the source item (e.g., PO number)"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the stock item"
    )
    
    # TODO: Add fields for:
    # - Location
    # - Minimum stock level
    # - Reorder point
    # - Category/Type
    # - Unit of measure
    
    def __str__(self):
        return f"{self.description} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        """
        Override save to add logging and validation.
        """
        logger.debug(f"Saving stock item: {self.description}")
        
        # Validate quantity is not negative
        if self.quantity < 0:
            logger.warning(f"Attempted to save stock item with negative quantity: {self.quantity}")
            raise ValueError("Stock quantity cannot be negative")
        
        # Validate unit cost is not negative
        if self.unit_cost < 0:
            logger.warning(f"Attempted to save stock item with negative unit cost: {self.unit_cost}")
            raise ValueError("Unit cost cannot be negative")
        
        super().save(*args, **kwargs)
        logger.info(f"Saved stock item: {self.description}")
    
    def split(self, split_quantity: Decimal) -> 'Stock':
        """
        Split this stock item into two items.
        
        Args:
            split_quantity: The quantity to split off into a new item
            
        Returns:
            The new stock item created from the split
        """
        logger.debug(f"Splitting stock item {self.id} - quantity: {split_quantity}")
        
        if split_quantity <= 0:
            raise ValueError("Split quantity must be positive")
            
        if split_quantity >= self.quantity:
            raise ValueError("Split quantity must be less than current quantity")
        
        # Calculate the proportion of the split
        proportion = split_quantity / self.quantity
        
        # Create new stock item
        new_stock = Stock.objects.create(
            job=self.job,
            description=self.description,
            quantity=split_quantity,
            unit_cost=self.unit_cost,
            date=timezone.now(),
            source='split',
            source_id=str(self.id),
            notes=f"Split from stock item {self.id}"
        )
        
        # Update this stock item
        self.quantity -= split_quantity
        self.save()
        
        logger.info(f"Split stock item {self.id} into {new_stock.id}")
        return new_stock 