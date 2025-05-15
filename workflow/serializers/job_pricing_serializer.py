import datetime
import logging
import uuid
from decimal import Decimal

from rest_framework import serializers

from workflow.enums import JobPricingStage
from workflow.models import JobPricing
from workflow.serializers.adjustment_entry_serializer import AdjustmentEntrySerializer
from workflow.serializers.material_entry_serializer import MaterialEntrySerializer
from timesheet.serializers import (
    TimeEntryForJobPricingSerializer as TimeEntrySerializer,
)

logger = logging.getLogger(__name__)
DEBUG_SERIALIZER = False  # Toggle serializer debugging


class JobPricingSerializer(serializers.ModelSerializer):
    time_entries = TimeEntrySerializer(many=True, required=False)
    material_entries = MaterialEntrySerializer(many=True, required=False)
    adjustment_entries = AdjustmentEntrySerializer(many=True, required=False)

    class Meta:
        model = JobPricing
        fields = [
            "id",
            "pricing_stage",
            "revision_number",
            "created_at",
            "updated_at",
            "time_entries",
            "material_entries",
            "adjustment_entries",
        ]

    def to_representation(self, instance):
        if DEBUG_SERIALIZER:
            logger.debug(
                "JobPricingSerializer to_representation called for instance %(id)s",
                {"id": instance.id},
            )
            logger.debug(
                "Raw material entries: %(entries)s",
                {"entries": list(instance.material_entries.all().values())},
            )

        representation = super().to_representation(instance)

        # Convert Decimal fields to float
        for key, value in representation.items():
            if isinstance(value, Decimal):
                representation[key] = float(value)
            elif isinstance(value, datetime.datetime):
                representation[key] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                representation[key] = str(value)

        # Ensure all entries are properly represented
        representation["time_entries"] = TimeEntrySerializer(
            instance.time_entries.all(), many=True
        ).data
        representation["material_entries"] = MaterialEntrySerializer(
            instance.material_entries.all(), many=True
        ).data
        representation["adjustment_entries"] = AdjustmentEntrySerializer(
            instance.adjustment_entries.all(), many=True
        ).data

        # logger.debug(f"Final representation: {representation}")
        return representation

    def to_internal_value(self, data):
        if DEBUG_SERIALIZER:
            logger.debug(
                "JobPricingSerializer to_internal_value called with data: %(data)s",
                {"data": data},
            )
        # Extract the nested entries data before validation
        time_data = data.get("time_entries", [])
        material_data = data.get("material_entries", [])
        adjustment_data = data.get("adjustment_entries", [])

        # logger.debug(f"Time data received: {time_data}")
        # logger.debug(f"Material data received: {material_data}")
        # logger.debug(f"Adjustment data received: {adjustment_data}")

        # Restructure data to match serializer fields
        restructured_data = {
            "time_entries": time_data,
            "material_entries": material_data,
            "adjustment_entries": adjustment_data,
        }

        if DEBUG_SERIALIZER:
            logger.debug(
                "Restructured data for internal value: %(restructured_data)s",
                {"restructured_data": restructured_data},
            )
        internal_value = super().to_internal_value(restructured_data)
        if DEBUG_SERIALIZER:
            logger.debug(
                "JobPricingSerializer to_internal_value result: %(internal_value)s",
                {"internal_value": internal_value},
            )
        return internal_value

    def validate(self, attrs):
        # logger.debug(f"JobPricingSerializer validate called with attrs: {attrs}")

        # Validate nested components
        for field in ["time_entries", "material_entries", "adjustment_entries"]:
            field_data = attrs.get(field, [])
            field_serializer = None
            if field == "time_entries":
                field_serializer = TimeEntrySerializer(data=field_data, many=True)
            elif field == "material_entries":
                field_serializer = MaterialEntrySerializer(data=field_data, many=True)
            elif field == "adjustment_entries":
                field_serializer = AdjustmentEntrySerializer(data=field_data, many=True)

            if field_serializer and not field_serializer.is_valid():
                logger.error(f"Validation errors in {field}: {field_serializer.errors}")
                raise serializers.ValidationError({field: field_serializer.errors})

        validated = super().validate(attrs)
        # logger.debug(f"After super().validate, data is: {validated}")
        return validated

    def update(self, instance, validated_data):
        # Update time entries
        if "time_entries" in validated_data and instance.pricing_stage != JobPricingStage.REALITY:
            # Delete existing entries
            instance.time_entries.all().delete()
            # Create new entries using serializer
            for time_entry_data in validated_data.pop("time_entries", []):
                time_entry_serializer = TimeEntrySerializer(data=time_entry_data)
                if time_entry_serializer.is_valid():
                    time_entry_serializer.save(job_pricing=instance)
                else:
                    logger.error(
                        f"Time entry validation failed: {time_entry_serializer.errors}"
                    )
                    raise serializers.ValidationError(
                        {"time_entries": time_entry_serializer.errors}
                    )
                
        # Remove time entries if the pricing stage is REALITY
        if "time_entries" in validated_data:
            validated_data.pop("time_entries")


        # Update material entries
        if "material_entries" in validated_data:
            # Delete existing entries
            instance.material_entries.all().delete()
            # Create new entries using serializer
            for material_entry_data in validated_data.pop("material_entries", []):
                material_entry_serializer = MaterialEntrySerializer(
                    data=material_entry_data
                )
                if material_entry_serializer.is_valid():
                    material_entry_serializer.save(job_pricing=instance)
                else:
                    logger.error(
                        "Material entry validation failed: %(errors)s",
                        {"errors": material_entry_serializer.errors},
                    )
                    raise serializers.ValidationError(
                        {"material_entries": material_entry_serializer.errors}
                    )

        # Update adjustment entries
        if "adjustment_entries" in validated_data:
            # Delete existing entries
            instance.adjustment_entries.all().delete()
            # Create new entries using serializer
            for adjustment_entry_data in validated_data.pop("adjustment_entries", []):
                adjustment_entry_serializer = AdjustmentEntrySerializer(
                    data=adjustment_entry_data
                )
                if adjustment_entry_serializer.is_valid():
                    adjustment_entry_serializer.save(job_pricing=instance)
                else:
                    logger.error(
                        "Adjustment entry validation failed: %(errors)s",
                        {"errors": adjustment_entry_serializer.errors},
                    )
                    raise serializers.ValidationError(
                        {"adjustment_entries": adjustment_entry_serializer.errors}
                    )

        # Update other fields (that aren't relationships, otherwise they would be handled above)
        related_fields = ["time_entries", "material_entries", "adjustment_entries"]
        for attr, value in validated_data.items():
            if attr not in related_fields:
                setattr(instance, attr, value)

        instance.save()
        return instance
