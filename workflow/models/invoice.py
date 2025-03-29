import uuid

from abc import abstractmethod

from decimal import Decimal

from django.db import models

from django.utils import timezone

from workflow.enums import InvoiceStatus


class BaseXeroInvoiceDocument(models.Model):
    """
    Abstract base class for Xero invoice-like documents (Invoices, Bills, Credit Notes).
    This represents financial documents that have line items and tax calculations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    xero_id = models.UUIDField(unique=True)
    number = models.CharField(max_length=255)
    client = models.ForeignKey("Client", on_delete=models.CASCADE)
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=50, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT
    )
    total_excl_tax = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    total_incl_tax = models.DecimalField(max_digits=10, decimal_places=2)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    xero_last_modified = models.DateTimeField()
    xero_last_synced = models.DateTimeField(null=True, blank=True, default=timezone.now)
    raw_json = models.JSONField()
    django_created_at = models.DateTimeField(auto_now_add=True)
    django_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.number} - {self.client.name}"

    @abstractmethod
    def get_line_items(self):
        """Return the queryset of line items related to this document."""
        pass

    @property
    def total_amount(self):
        """Calculate the total amount by summing up the related line items."""
        return sum(item.line_amount_excl_tax for item in self.get_line_items())


class BaseLineItem(models.Model):
    """
    Abstract base class for all line items (Invoice, Bill, Credit Note items).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    xero_line_id = models.UUIDField(unique=True, default=uuid.uuid4)
    description = models.TextField()
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=Decimal("1.00")
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    line_amount_excl_tax = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    line_amount_incl_tax = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    account = models.ForeignKey(
        "XeroAccount", on_delete=models.SET_NULL, null=True, blank=True
    )
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.description} - {self.line_amount_excl_tax}"

    @property
    def total_price(self):
        """Compute the total price of the line item including tax."""
        return (self.unit_price or Decimal("0.00")) * (self.quantity or Decimal("1.00"))


# Concrete Document Classes


class Invoice(BaseXeroInvoiceDocument):
    job = models.OneToOneField(
        "Job", on_delete=models.CASCADE, related_name="invoice", null=True, blank=True
    )
    online_url = models.URLField(null=True, blank=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ["-date", "number"]

    def get_line_items(self):
        return self.line_items.all()


class Bill(BaseXeroInvoiceDocument):
    class Meta:
        verbose_name = "Bill"
        verbose_name_plural = "Bills"
        ordering = ["-date", "number"]

    @property
    def supplier(self):
        """Return the client as 'supplier' for bills."""
        return self.client

    @supplier.setter
    def supplier(self, value):
        self.client = value

    def get_line_items(self):
        return self.line_items.all()


class CreditNote(BaseXeroInvoiceDocument):
    # Note that Xero has a few extra fields we don't have mapped
    # allocations
    # fully_paid_on_date
    # maybe more.  We can add them as needed.

    class Meta:
        verbose_name = "Credit Note"
        verbose_name_plural = "Credit Notes"
        ordering = ["-date"]

    def __str__(self):
        return f"Credit Note {self.number} ({self.status})"

    def get_line_items(self):
        return self.line_items.all()


# Concrete Line Item Classes


class InvoiceLineItem(BaseLineItem):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="line_items"
    )

    class Meta:
        verbose_name = "Invoice Line Item"
        verbose_name_plural = "Invoice Line Items"


class BillLineItem(BaseLineItem):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="line_items")

    class Meta:
        verbose_name = "Bill Line Item"
        verbose_name_plural = "Bill Line Items"


class CreditNoteLineItem(BaseLineItem):
    credit_note = models.ForeignKey(
        CreditNote, on_delete=models.CASCADE, related_name="line_items"
    )

    class Meta:
        verbose_name = "Credit Note Line Item"
        verbose_name_plural = "Credit Note Line Items"
