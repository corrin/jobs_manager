import logging
from decimal import Decimal

from rest_framework import serializers

from timesheet.models import TimeEntry

logger = logging.getLogger(__name__)


class TimeEntrySerializer(serializers.ModelSerializer):
    """
    Basic TimeEntry serializer for use with Parts.
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
            "part",
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
            "hours",
            "date",
            "note",
            "is_billable",
            "wage_rate_multiplier"
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
        return str(obj.staff.id) if obj.staff else None

    def get_timesheet_date(self, obj):
        return obj.date.strftime("%Y-%m-%d") if obj.date else None
    
    def get_staff_name(self, obj):
        return obj.staff.get_display_name() if obj.staff else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert UUID id field to string for JSON serialization
        if 'id' in representation and representation['id']:
            representation['id'] = str(representation['id'])
        
        # Convert part UUID to string if present
        if 'part' in representation and representation['part']:
            representation['part'] = str(representation['part'])
            
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
            "part",
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
        return str(obj.part.job_pricing.id)

    def get_job_number(self, obj):
        return obj.part.job_pricing.job.job_number

    def get_job_name(self, obj):
        return obj.part.job_pricing.job.name

    def get_hours(self, obj):
        return float(obj.hours)

    def get_timesheet_date(self, obj):
        return obj.date.strftime("%Y-%m-%d")

    def get_hours_spent(self, obj):
        return obj.part.job_pricing.total_hours

    def get_estimated_hours(self, obj):
        return (
            obj.part.job_pricing.job.latest_estimate_pricing.total_hours
            if obj.part.job_pricing.job.latest_estimate_pricing
            else 0
        )

    def get_staff_id(self, obj):
        return str(obj.staff.id)
