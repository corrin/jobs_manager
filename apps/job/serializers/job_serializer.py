import logging

from rest_framework import serializers

from apps.accounting.models.invoice import Invoice
from apps.accounting.models.quote import Quote
from apps.client.models import Client, ClientContact
from apps.job.models import Job, JobFile

from .costing_serializer import CostSetSerializer
from .job_file_serializer import JobFileSerializer
from .job_pricing_serializer import JobPricingSerializer
from .quote_spreadsheet_serializer import QuoteSpreadsheetSerializer

logger = logging.getLogger(__name__)
DEBUG_SERIALIZER = False


class InvoiceSerializer(serializers.ModelSerializer):
    total_excl_tax = serializers.FloatField()
    total_incl_tax = serializers.FloatField()
    amount_due = serializers.FloatField()
    tax = serializers.FloatField(required=False)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "xero_id",
            "number",
            "status",
            "date",
            "due_date",
            "total_excl_tax",
            "total_incl_tax",
            "amount_due",
            "tax",
            "online_url",
        ]


class QuoteSerializer(serializers.ModelSerializer):
    total_excl_tax = serializers.FloatField()
    total_incl_tax = serializers.FloatField()

    class Meta:
        model = Quote
        fields = [
            "id",
            "xero_id",
            "status",
            "date",
            "total_excl_tax",
            "total_incl_tax",
            "online_url",
        ]


class JobSerializer(serializers.ModelSerializer):
    # Legacy JobPricing fields (deprecated but kept for backward compatibility)
    latest_estimate_pricing = JobPricingSerializer(required=False)
    latest_quote_pricing = JobPricingSerializer(required=False)
    latest_reality_pricing = JobPricingSerializer(required=False)
    # New CostSet fields (current system)
    latest_estimate = serializers.SerializerMethodField()
    latest_quote = serializers.SerializerMethodField()
    latest_actual = serializers.SerializerMethodField()
    quoted = serializers.BooleanField(read_only=True)
    invoiced = serializers.BooleanField(read_only=True)
    quote = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()

    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        write_only=False,  # Allow read access
    )
    client_name = serializers.CharField(source="client.name", read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=ClientContact.objects.all(),
        source="contact",
        write_only=False,  # Allow read access
        required=False,
        allow_null=True,
    )
    contact_name = serializers.CharField(
        source="contact.name", read_only=True, required=False
    )
    job_status = serializers.CharField(source="status")
    job_files = JobFileSerializer(
        source="files", many=True, required=False
    )  # To prevent conflicts with PUTTING only one file

    # Quote spreadsheet relationship
    quote_sheet = QuoteSpreadsheetSerializer(read_only=True, required=False)

    def get_latest_estimate(self, obj):
        """Get the latest estimate CostSet"""
        cost_set = obj.get_latest("estimate")
        return CostSetSerializer(cost_set).data if cost_set else None

    def get_latest_quote(self, obj):
        """Get the latest quote CostSet"""
        cost_set = obj.get_latest("quote")
        return CostSetSerializer(cost_set).data if cost_set else None

    def get_latest_actual(self, obj):
        """Get the latest actual CostSet"""
        cost_set = obj.get_latest("actual")
        return CostSetSerializer(cost_set).data if cost_set else None

    def get_quote(self, obj):
        raw_quote = getattr(obj, "quote", None)
        logger.debug(f"Getting quote for job {obj.id}: {raw_quote} | {type(raw_quote)}")

        if raw_quote is not None:
            serialized = QuoteSerializer(raw_quote, context=self.context).data
            logger.debug(f"Serialized quote data: {serialized}")
            return serialized
        return None

    def get_invoice(self, obj):
        raw_invoice = getattr(obj, "invoice", None)
        logger.debug(
            f"Getting invoice for job {obj.id}: {raw_invoice} | {type(raw_invoice)}"
        )

        if raw_invoice is not None:
            serialized = InvoiceSerializer(raw_invoice, context=self.context).data
            logger.debug(f"Serialized invoice data: {serialized}")
            return serialized
        return None

    class Meta:
        model = Job
        fields = [
            "id",
            "name",
            "client_id",
            "client_name",
            "contact_id",
            "contact_name",
            "contact_person",
            "contact_email",
            "contact_phone",
            "job_number",
            "notes",
            "order_number",
            "created_at",
            "updated_at",
            "material_gauge_quantity",
            "description",
            # Legacy JobPricing fields (deprecated but kept for backward compatibility)
            "latest_estimate_pricing",
            "latest_quote_pricing",
            "latest_reality_pricing",
            # New CostSet fields (current system)
            "latest_estimate",
            "latest_quote",
            "latest_actual",
            "job_status",
            "delivery_date",
            "paid",
            "quote_acceptance_date",
            "job_is_valid",
            "job_files",
            "charge_out_rate",
            "pricing_methodology",
            "quote_sheet",
            "quoted",
            "invoiced",
            "quote",
            "invoice",
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

        # Remove read-only/computed fields to avoid AttributeError
        validated_data.pop("quoted", None)
        validated_data.pop("invoiced", None)

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

        pricing_methodologys = {
            "latest_estimate_pricing": instance.latest_estimate_pricing,
            "latest_quote_pricing": instance.latest_quote_pricing,
            "latest_reality_pricing": instance.latest_reality_pricing,
        }

        for pricing_methodology, pricing_instance in pricing_methodologys.items():
            pricing_data = validated_data.get(pricing_methodology)
            if pricing_data:
                if DEBUG_SERIALIZER:
                    logger.debug(
                        "Creating %(type)s serializer with data: %(data)s",
                        {
                            "type": pricing_methodology,
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
                    logger.debug(f"{pricing_methodology} serializer is valid")
                    pricing_serializer.save()
                else:
                    logger.error(
                        "%(type)s serializer validation failed: %(errors)s",
                        {
                            "type": pricing_methodology,
                            "errors": pricing_serializer.errors,
                        },
                    )
                    raise serializers.ValidationError(
                        {pricing_methodology: pricing_serializer.errors}
                    )

        staff = self.context["request"].user if "request" in self.context else None
        instance.save(staff=staff)
        return instance


class CompleteJobSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    job_status = serializers.CharField(source="status")

    class Meta:
        model = Job
        fields = ["id", "job_number", "name", "client_name", "updated_at", "job_status"]
