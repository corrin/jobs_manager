from rest_framework import serializers

from job.helpers import decimal_to_float
from job.models import MaterialEntry


class MaterialEntrySerializer(serializers.ModelSerializer):
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    revenue = serializers.SerializerMethodField()
    description = serializers.CharField(allow_blank=True)
    item_code = serializers.CharField(allow_blank=True, required=False)
    comments = serializers.CharField(allow_blank=True, required=False)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    revenue = serializers.SerializerMethodField(read_only=True)
    cost = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MaterialEntry
        fields = [
            "id",
            "part",
            "item_code",
            "description",
            "quantity",
            "unit_cost",
            "unit_revenue",
            "revenue",
            "cost",
            "comments",
            "created_at",
            "updated_at",
        ]

    def get_revenue(self, obj):
        # Use the model's revenue property
        return obj.revenue

    def get_cost(self, obj):
        # Use the model's cost method
        return decimal_to_float(obj.cost)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert UUID id field to string for JSON serialization
        if 'id' in representation and representation['id']:
            representation['id'] = str(representation['id'])
        
        # Convert part UUID to string if present
        if 'part' in representation and representation['part']:
            representation['part'] = str(representation['part'])
            
        return representation
