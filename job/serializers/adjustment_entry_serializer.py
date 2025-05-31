from rest_framework import serializers

from job.models import AdjustmentEntry


class AdjustmentEntrySerializer(serializers.ModelSerializer):
    revenue = serializers.SerializerMethodField(read_only=True)
    cost = serializers.SerializerMethodField(read_only=True)
    description = serializers.CharField(allow_blank=True, required=False)
    comments = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = AdjustmentEntry
        fields = [
            "id",
            "part",
            "description",
            "cost_adjustment",
            "price_adjustment",
            "comments",
            "revenue",
            "cost",
            "created_at",
            "updated_at",
        ]

    def get_revenue(self, obj):
        # Use price_adjustment for revenue
        return obj.price_adjustment

    def get_cost(self, obj):
        # Use cost_adjustment for cost
        return obj.cost_adjustment

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert UUID id field to string for JSON serialization
        if 'id' in representation and representation['id']:
            representation['id'] = str(representation['id'])
        
        # Convert part UUID to string if present
        if 'part' in representation and representation['part']:
            representation['part'] = str(representation['part'])
            
        return representation
