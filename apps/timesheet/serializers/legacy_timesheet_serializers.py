import logging
from decimal import Decimal

from rest_framework import serializers

from apps.accounts.models import Staff
from apps.job.models import Job, JobPricing
from apps.timesheet.models import TimeEntry

logger = logging.getLogger(__name__)


class TimeEntryForJobPricingSerializer(serializers.ModelSerializer):
    """
    Serializer used for JobPricing context.
    Includes the original fields of TimeEntrySerializer and adds staff_id and
    timesheet_date to display a link for the timesheet in edit_job_view_ajax.html
    """

    total_minutes = serializers.SerializerMethodField()
    revenue = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()
    description = serializers.CharField(allow_blank=True)
    staff_id = serializers.SerializerMethodField()
    timesheet_date = serializers.SerializerMethodField()
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = TimeEntry
        fields = [
            "id",
            "description",
            "items",
            "minutes_per_item",
            "wage_rate",
            "charge_out_rate",
            "total_minutes",
            "revenue",
            "cost",
            "staff_id",
            "timesheet_date",
            "staff_name",
        ]

    def get_total_minutes(self, obj):
        return (
            (obj.items * obj.minutes_per_item).quantize(
                Decimal("0.01"), rounding="ROUND_HALF_UP"
            )
            if obj.items and obj.minutes_per_item
            else 0
        )

    def get_revenue(self, obj):
        return obj.revenue

    def get_cost(self, obj):
        return obj.cost

    def get_staff_id(self, obj):
        logger.warning(f"TimeEntry {obj.id} has no associated staff.")
        return str(obj.staff.id) if obj.staff else None

    def get_timesheet_date(self, obj):
        return obj.date.strftime("%Y-%m-%d") if obj.date else None

    def get_staff_name(self, obj):
        return obj.staff.get_display_name() if obj.staff else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        logger.debug(f"Serialized TimeEntry: {representation}")
        return representation


class TimeEntryForTimeEntryViewSerializer(serializers.ModelSerializer):
    """
    Serializer used for TimeEntryView.
    Includes all fields defined in the new serializer.
    """

    description = serializers.CharField(allow_blank=True)

    job_pricing_id = serializers.SerializerMethodField()
    job_number = serializers.SerializerMethodField()
    job_name = serializers.SerializerMethodField()
    hours = serializers.SerializerMethodField()
    is_billable = serializers.BooleanField()
    notes = serializers.CharField(source="note", allow_blank=True)
    rate_multiplier = serializers.FloatField(source="wage_rate_multiplier")
    timesheet_date = serializers.SerializerMethodField()
    hours_spent = serializers.SerializerMethodField()
    estimated_hours = serializers.SerializerMethodField()
    staff_id = serializers.SerializerMethodField()

    mins_per_item = serializers.DecimalField(
        source="minutes_per_item", max_digits=5, decimal_places=2, required=False
    )
    items = serializers.IntegerField(required=False)

    class Meta:
        model = TimeEntry
        fields = [
            "id",
            "description",
            "items",
            "mins_per_item",
            "wage_rate",
            "charge_out_rate",
            "job_pricing_id",
            "job_number",
            "job_name",
            "hours",
            "is_billable",
            "notes",
            "rate_multiplier",
            "timesheet_date",
            "hours_spent",
            "estimated_hours",
            "staff_id",
        ]

    def get_revenue(self, obj):
        return obj.revenue

    def get_cost(self, obj):
        return obj.cost

    def get_job_pricing_id(self, obj):
        return str(obj.job_pricing.id)

    def get_job_number(self, obj):
        return obj.job_pricing.job.job_number

    def get_job_name(self, obj):
        return obj.job_pricing.job.name

    def get_hours(self, obj):
        return float(obj.hours)

    def get_timesheet_date(self, obj):
        return obj.date.strftime("%Y-%m-%d")

    def get_hours_spent(self, obj):
        return obj.job_pricing.total_hours

    def get_estimated_hours(self, obj):
        return (
            obj.job_pricing.job.latest_estimate_pricing.total_hours
            if obj.job_pricing.job.latest_estimate_pricing
            else 0
        )

    def get_staff_id(self, obj):
        return str(obj.staff.id)


class TimeEntryAPISerializer(serializers.ModelSerializer):
    """
    Serializer optimized for Vue.js frontend API communication.
    Maps Django model fields to frontend expectations.
    """

    # Map frontend field names to Django model fields
    jobPricingId = serializers.CharField(source="job_pricing.id", read_only=True)
    jobNumber = serializers.CharField(
        source="job_pricing.job.job_number", read_only=True
    )
    jobName = serializers.CharField(source="job_pricing.job.name", read_only=True)
    isBillable = serializers.BooleanField(source="is_billable")
    notes = serializers.CharField(source="note", allow_blank=True, required=False)
    rateMultiplier = serializers.DecimalField(
        source="wage_rate_multiplier", max_digits=5, decimal_places=2
    )
    timesheetDate = serializers.DateField(source="date", format="%Y-%m-%d")
    hoursSpent = serializers.DecimalField(
        source="job_pricing.total_hours",
        read_only=True,
        max_digits=10,
        decimal_places=2,
    )
    estimatedHours = serializers.SerializerMethodField()
    staffId = serializers.CharField(source="staff.id", read_only=True)
    minsPerItem = serializers.DecimalField(
        source="minutes_per_item",
        max_digits=8,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    wageRate = serializers.DecimalField(
        source="wage_rate", max_digits=10, decimal_places=2
    )
    chargeOutRate = serializers.DecimalField(
        source="charge_out_rate", max_digits=10, decimal_places=2
    )

    class Meta:
        model = TimeEntry
        fields = [
            "id",
            "description",
            "jobPricingId",
            "jobNumber",
            "jobName",
            "hours",
            "isBillable",
            "notes",
            "rateMultiplier",
            "timesheetDate",
            "hoursSpent",
            "estimatedHours",
            "staffId",
            "items",
            "minsPerItem",
            "wageRate",
            "chargeOutRate",
        ]

    def get_estimatedHours(self, obj):
        """Get estimated hours from job's latest estimate pricing."""
        try:
            if (
                obj.job_pricing
                and obj.job_pricing.job
                and obj.job_pricing.job.latest_estimate_pricing
            ):
                return float(obj.job_pricing.job.latest_estimate_pricing.total_hours)
            return 0.0
        except:
            return 0.0

    def to_representation(self, instance):
        """Convert decimal fields to float for JSON serialization."""
        representation = super().to_representation(instance)

        # Convert Decimal fields to float for frontend
        decimal_fields = [
            "hours",
            "hoursSpent",
            "estimatedHours",
            "rateMultiplier",
            "wageRate",
            "chargeOutRate",
            "minsPerItem",
        ]
        for field in decimal_fields:
            if field in representation and representation[field] is not None:
                representation[field] = float(representation[field])

        return representation


class StaffAPISerializer(serializers.ModelSerializer):
    """
    Serializer for Staff model optimized for Vue.js frontend.
    """

    name = serializers.SerializerMethodField()
    firstName = serializers.CharField(source="first_name", read_only=True)
    lastName = serializers.CharField(source="last_name", read_only=True)
    avatarUrl = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = [
            "id",
            "name",
            "firstName",
            "lastName",
            "email",
            "avatarUrl",
        ]

    def get_name(self, obj):
        """Get full display name."""
        return obj.get_display_name()

    def get_avatarUrl(self, obj):
        """Get avatar URL - returns icon URL if available, otherwise None."""
        if obj.icon:
            # Use Django's build_absolute_uri to generate full URL
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.icon.url)
            return obj.icon.url
        return None  # Return None instead of empty string for consistent handling


class JobPricingAPISerializer(serializers.ModelSerializer):
    """
    Serializer for JobPricing model optimized for Vue.js frontend.
    """

    jobId = serializers.CharField(source="job.id", read_only=True)
    jobNumber = serializers.CharField(source="job.job_number", read_only=True)
    jobName = serializers.CharField(source="job.name", read_only=True)
    taskName = serializers.SerializerMethodField()
    isBillable = serializers.BooleanField(read_only=True)
    chargeOutRate = serializers.DecimalField(
        source="charge_out_rate", max_digits=10, decimal_places=2, read_only=True
    )
    estimatedHours = serializers.DecimalField(
        source="estimated_hours", max_digits=10, decimal_places=2, read_only=True
    )
    totalHours = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    displayName = serializers.SerializerMethodField()

    class Meta:
        model = JobPricing
        fields = [
            "id",
            "jobId",
            "jobNumber",
            "jobName",
            "taskName",
            "chargeOutRate",
            "estimatedHours",
            "totalHours",
            "isBillable",
            "displayName",
        ]

    def get_taskName(self, obj):
        """Generate a task name based on the pricing stage."""
        return f"{obj.get_pricing_stage_display()}"

    def get_displayName(self, obj):
        """Create display name for job selection."""
        task_name = self.get_taskName(obj)
        return f"{obj.job.job_number} - {obj.job.name} ({task_name})"

    def to_representation(self, instance):
        """Convert decimal fields to float for JSON serialization."""
        representation = super().to_representation(instance)

        # Convert Decimal fields to float for frontend
        decimal_fields = ["chargeOutRate", "estimatedHours", "totalHours"]
        for field in decimal_fields:
            if field in representation and representation[field] is not None:
                representation[field] = float(representation[field])

        return representation


class TimesheetJobAPISerializer(serializers.ModelSerializer):
    """
    Serializer for Job model optimized for timesheet job selection.
    Uses the modern CostSet system instead of JobPricing.
    """

    jobId = serializers.CharField(source="id", read_only=True)
    jobNumber = serializers.CharField(source="job_number", read_only=True)
    jobName = serializers.CharField(source="name", read_only=True)
    clientName = serializers.CharField(source="client.name", read_only=True)
    taskName = serializers.SerializerMethodField()
    isBillable = serializers.BooleanField(default=True, read_only=True)
    chargeOutRate = serializers.DecimalField(
        source="charge_out_rate", max_digits=10, decimal_places=2, read_only=True
    )
    estimatedHours = serializers.SerializerMethodField()
    totalHours = serializers.SerializerMethodField()
    displayName = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "jobId",
            "jobNumber",
            "jobName",
            "clientName",
            "taskName",
            "chargeOutRate",
            "estimatedHours",
            "totalHours",
            "isBillable",
            "displayName",
            "status",
        ]

    def get_taskName(self, obj):
        """Generate a task name for timesheet context."""
        return "Time Entry"

    def get_estimatedHours(self, obj):
        """Get estimated hours from the latest estimate CostSet."""
        estimate_cost_set = obj.get_latest("estimate")
        if estimate_cost_set and estimate_cost_set.summary:
            return estimate_cost_set.summary.get("hours", 0)
        return 0

    def get_totalHours(self, obj):
        """Get actual hours from the latest actual CostSet."""
        actual_cost_set = obj.get_latest("actual")
        if actual_cost_set and actual_cost_set.summary:
            return actual_cost_set.summary.get("hours", 0)
        return 0

    def get_displayName(self, obj):
        """Create display name for job selection."""
        client_part = f" - {obj.client.name}" if obj.client else ""
        return f"{obj.job_number} - {obj.name}{client_part}"

    def to_representation(self, instance):
        """Convert decimal fields to float for JSON serialization."""
        representation = super().to_representation(instance)

        # Convert Decimal fields to float for frontend
        decimal_fields = ["chargeOutRate", "estimatedHours", "totalHours"]
        for field in decimal_fields:
            if field in representation and representation[field] is not None:
                representation[field] = float(representation[field])

        return representation
