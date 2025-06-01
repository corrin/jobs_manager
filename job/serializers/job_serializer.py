import logging

from rest_framework import serializers

from workflow.models import Client
from job.models import Job, JobFile
from .job_file_serializer import JobFileSerializer
from .job_pricing_serializer import JobPricingSerializer

logger = logging.getLogger(__name__)
DEBUG_SERIALIZER = False


class JobSerializer(serializers.ModelSerializer):
    latest_estimate_pricing = JobPricingSerializer(required=False)
    latest_quote_pricing = JobPricingSerializer(required=False)
    latest_reality_pricing = JobPricingSerializer(required=False)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        write_only=True,
    )
    client_name = serializers.CharField(source="client.name", read_only=True)
    job_status = serializers.CharField(source="status")
    job_files = JobFileSerializer(
        source="files", many=False, required=False
    )  # To prevent conflicts with PUTTING only one file

    class Meta:
        model = Job
        fields = [
            "id",
            "name",
            "client_id",
            "client_name",
            "contact_person",
            "contact_email",  # Added contact_email
            "contact_phone",
            "job_number",
            "notes",
            "order_number",
            "created_at",
            "updated_at",
            "material_gauge_quantity",
            "description",
            "latest_estimate_pricing",
            "latest_quote_pricing",
            "latest_reality_pricing",
            "job_status",
            "delivery_date",
            "paid",
            "quote_acceptance_date",
            "job_is_valid",
            "job_files",
            "charge_out_rate",
            "pricing_methodology",
        ]

    def validate(self, attrs):
        if DEBUG_SERIALIZER:
            logger.debug(f"JobSerializer validate called with attrs: {attrs}")
        # Validate nested pricing serializers
        nested_pricings = [
            "latest_estimate_pricing",
            "latest_quote_pricing",
            "latest_reality_pricing",
        ]
        for pricing_key in nested_pricings:
            pricing_data = attrs.get(pricing_key)
            if pricing_data:
                pricing_serializer = JobPricingSerializer(
                    data=pricing_data, partial=True
                )
                if not pricing_serializer.is_valid():
                    logger.error(
                        "Validation errors in %(key)s: %(errors)s",
                        {
                            "key": pricing_key,
                            "errors": pricing_serializer.errors,
                        },
                    )
                    raise serializers.ValidationError(
                        {pricing_key: pricing_serializer.errors}
                    )

        validated = super().validate(attrs)
        if DEBUG_SERIALIZER:
            logger.debug(f"After super().validate, data is: {validated}")
        return validated

    def update(self, instance, validated_data):
        logger.debug(f"JobSerializer update called for instance {instance.id}")
        logger.debug(f"Validated data received: {validated_data}")

        # Handle job files data first
        files_data = validated_data.pop("files", None)
        if files_data:
            for file_data in files_data:
                try:
                    job_file = JobFile.objects.get(id=file_data["id"], job=instance)
                    file_serializer = JobFileSerializer(
                        instance=job_file,
                        data=file_data,
                        partial=True,
                        context=self.context,
                    )
                    if file_serializer.is_valid():
                        file_serializer.save()
                    else:
                        logger.error(
                            f"JobFile validation failed: {file_serializer.errors}"
                        )
                        raise serializers.ValidationError(
                            {"job_files": file_serializer.errors}
                        )
                except JobFile.DoesNotExist:
                    logger.warning(
                        (
                            f"JobFile with id {file_data.get('id')} "
                            f"not found for job {instance.id}"
                        )
                    )
                except Exception as e:
                    logger.error(f"Error updating JobFile: {str(e)}")
                    raise serializers.ValidationError(f"Error updating file: {str(e)}")

        # Handle basic job fields next
        for attr, value in validated_data.items():
            if attr not in [
                "latest_estimate_pricing",
                "latest_quote_pricing",
                "latest_reality_pricing",
            ]:
                setattr(instance, attr, value)

        pricing_types = {
            "latest_estimate_pricing": instance.latest_estimate_pricing,
            "latest_quote_pricing": instance.latest_quote_pricing,
            "latest_reality_pricing": instance.latest_reality_pricing,
        }

        for pricing_type, pricing_instance in pricing_types.items():
            pricing_data = validated_data.get(pricing_type)
            if pricing_data:
                if DEBUG_SERIALIZER:
                    logger.debug(
                        "Creating %(type)s serializer with data: %(data)s",
                        {
                            "type": pricing_type,
                            "data": pricing_data,
                        },
                    )
                pricing_serializer = JobPricingSerializer(
                    instance=pricing_instance,
                    data=pricing_data,
                    partial=True,
                    context=self.context,
                )

                if pricing_serializer.is_valid():
                    logger.debug(f"{pricing_type} serializer is valid")
                    pricing_serializer.save()
                else:
                    logger.error(
                        "%(type)s serializer validation failed: %(errors)s",
                        {
                            "type": pricing_type,
                            "errors": pricing_serializer.errors,
                        },
                    )
                    raise serializers.ValidationError(
                        {pricing_type: pricing_serializer.errors}
                    )

        staff = self.context["request"].user if "request" in self.context else None
        instance.save(staff=staff)
        return instance
    

class CompleteJobSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    job_status = serializers.CharField(source="status")

    class Meta:
        model = Job
        fields = [
            "id",
            "job_number",
            "name",
            "client_name",
            "updated_at",
            "job_status"
        ]
