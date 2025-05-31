import datetime
import logging
import uuid
from decimal import Decimal

from rest_framework import serializers

from workflow.enums import JobPricingType
from job.models import JobPricing
from .part_serializer import PartSerializer

logger = logging.getLogger(__name__)
DEBUG_SERIALIZER = False  # Toggle serializer debugging


class JobPricingSerializer(serializers.ModelSerializer):
    parts = PartSerializer(many=True, required=False)

    class Meta:
        model = JobPricing
        fields = [
            "id",
            "pricing_type",
            "revision_number",
            "created_at",
            "updated_at",
            "parts",
        ]

    def to_representation(self, instance):
        if DEBUG_SERIALIZER:
            logger.debug(
                "JobPricingSerializer to_representation called for instance %(id)s",
                {"id": instance.id},
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

        # Ensure all parts are properly represented
        representation["parts"] = PartSerializer(
            instance.parts.all(), many=True
        ).data

        # logger.debug(f"Final representation: {representation}")
        return representation

    def to_internal_value(self, data):
        if DEBUG_SERIALIZER:
            logger.debug(
                "JobPricingSerializer to_internal_value called with data: %(data)s",
                {"data": data},
            )
        
        # With the new part-based architecture, we expect parts data
        parts_data = data.get("parts", [])
        
        # Restructure data to match serializer fields
        restructured_data = {
            "parts": parts_data,
        }
        
        # Include other job pricing fields if present
        for field in ["pricing_type", "revision_number"]:
            if field in data:
                restructured_data[field] = data[field]

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
        if DEBUG_SERIALIZER:
            logger.debug(f"JobPricingSerializer validate called with attrs: {attrs}")

        # Validate parts
        parts_data = attrs.get("parts", [])
        if parts_data:
            parts_serializer = PartSerializer(data=parts_data, many=True)
            if not parts_serializer.is_valid():
                logger.error(f"Validation errors in parts: {parts_serializer.errors}")
                raise serializers.ValidationError({"parts": parts_serializer.errors})

        validated = super().validate(attrs)
        if DEBUG_SERIALIZER:
            logger.debug(f"After super().validate, data is: {validated}")
        return validated

    def create(self, validated_data):
        if DEBUG_SERIALIZER:
            logger.debug(f"JobPricingSerializer create called with validated_data: {validated_data}")
        
        # Extract parts data
        parts_data = validated_data.pop('parts', [])
        
        # Create the job pricing instance
        job_pricing = JobPricing.objects.create(**validated_data)
        
        # Create parts with their entries
        for part_data in parts_data:
            part_data['job_pricing'] = job_pricing
            part_serializer = PartSerializer(data=part_data)
            if part_serializer.is_valid():
                part_serializer.save()
            else:
                logger.error(f"Part validation failed during create: {part_serializer.errors}")
                raise serializers.ValidationError({"parts": part_serializer.errors})
        
        return job_pricing

    def update(self, instance, validated_data):
        if DEBUG_SERIALIZER:
            logger.debug(f"JobPricingSerializer update called with validated_data: {validated_data}")
        
        # Update parts
        if "parts" in validated_data:
            parts_data = validated_data.pop("parts")
            
            # Delete existing parts (which will cascade delete their entries)
            instance.parts.all().delete()
            
            # Create new parts with their entries
            for part_data in parts_data:
                part_data['job_pricing'] = instance
                part_serializer = PartSerializer(data=part_data)
                if part_serializer.is_valid():
                    part_serializer.save()
                else:
                    logger.error(f"Part validation failed: {part_serializer.errors}")
                    raise serializers.ValidationError({"parts": part_serializer.errors})

        # Update other job pricing fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
