from django.core.exceptions import ValidationError
from django.db import models, transaction


class CompanyDefaults(models.Model):
    company_name = models.CharField(max_length=255, primary_key=True)
    is_primary = models.BooleanField(default=True, unique=True)
    time_markup = models.DecimalField(max_digits=5, decimal_places=2, default=0.3)
    materials_markup = models.DecimalField(max_digits=5, decimal_places=2, default=0.2)
    charge_out_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=105.00
    )  # rate per hour
    wage_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=32.00
    )  # rate per hour

    starting_job_number = models.IntegerField(
        default=1,
        help_text="Helper field to set the starting job number based on the latest paper job",
    )
    starting_po_number = models.IntegerField(
        default=1, help_text="Helper field to set the starting purchase order number"
    )
    po_prefix = models.CharField(
        max_length=10,
        default="PO-",
        help_text="Prefix for purchase order numbers (e.g., PO-, JO-)",
    )

    # Google Sheets integration for Job Quotes
    master_quote_template_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL to the master Google Sheets quote template",
    )

    master_quote_template_id = models.CharField(
        null=True,
        blank=True,
        help_text="Google Sheets ID for the quote template",
        max_length=100,
    )

    gdrive_quotes_folder_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL to the Google Drive folder for storing quotes",
    )

    gdrive_quotes_folder_id = models.CharField(
        null=True,
        blank=True,
        help_text="Google Drive folder ID for storing quotes",
        max_length=100,
    )

    # Xero integration
    xero_tenant_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="The Xero tenant ID to use for this company",
    )

    # Default working hours (Mon-Fri, 7am - 3pm)
    mon_start = models.TimeField(default="07:00")
    mon_end = models.TimeField(default="15:00")
    tue_start = models.TimeField(default="07:00")
    tue_end = models.TimeField(default="15:00")
    wed_start = models.TimeField(default="07:00")
    wed_end = models.TimeField(default="15:00")
    thu_start = models.TimeField(default="07:00")
    thu_end = models.TimeField(default="15:00")
    fri_start = models.TimeField(default="07:00")
    fri_end = models.TimeField(default="15:00")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_xero_sync = models.DateTimeField(
        null=True, blank=True, help_text="The last time Xero data was synchronized"
    )
    last_xero_deep_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The last time a deep Xero sync was performed (looking back 90 days)",
    )

    # Shop client configuration
    shop_client_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name of the internal shop client for tracking shop work (e.g., 'MSM (Shop)')",
    )

    # KPI thresholds
    billable_threshold_green = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=45.0,
        verbose_name="Green Threshold of Billable Hours",
        help_text="Daily billable hours above this threshold are marked in green",
    )
    billable_threshold_amber = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.0,
        verbose_name="Amber Threshold of Billable Hours",
        help_text="Daily billable hours between this threshold and the green threshold are marked in amber",
    )
    daily_gp_target = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1250.0,
        verbose_name="Daily Goal of Gross Profit",
        help_text="Daily gross profit goal in dolars",
    )
    shop_hours_target_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.0,
        verbose_name="Hours percentage goal in Shop Jobs",
        help_text="Target percentage of hours worked in shop jobs",
    )

    class Meta:
        verbose_name = "Company Defaults"
        verbose_name_plural = "Company Defaults"

    def save(self, *args, **kwargs):
        print(
            f"DEBUG: CompanyDefaults.save called with shop_client_name = {self.shop_client_name}"
        )
        if not self.pk and CompanyDefaults.objects.exists():
            raise ValidationError("There can be only one CompanyDefaults instance")
        self.is_primary = True
        print(
            f"DEBUG: About to call super().save() with shop_client_name = {self.shop_client_name}"
        )
        result = super().save(*args, **kwargs)
        print(
            f"DEBUG: After super().save(), shop_client_name = {self.shop_client_name}"
        )
        return result

    @classmethod
    def get_instance(cls) -> "CompanyDefaults":
        """
        Get the singleton instance.
        This is the preferred way to get the CompanyDefaults instance.
        """
        with transaction.atomic():
            return cls.objects.get()

    @property
    def llm_api_key(self):
        """
        Returns the API key of the active LLM provider.
        """
        from .ai_provider import AIProvider

        active_provider = AIProvider.objects.filter(default=True).first()
        return active_provider.api_key if active_provider else None

    def __str__(self):
        return self.company_name
