from rest_framework import serializers
from uuid import UUID
from job.models import Part
from .adjustment_entry_serializer import AdjustmentEntrySerializer
from .material_entry_serializer import MaterialEntrySerializer
from timesheet.serializers import TimeEntrySerializer


class PartSerializer(serializers.ModelSerializer):
    time_entries = TimeEntrySerializer(many=True, required=False)
    material_entries = MaterialEntrySerializer(many=True, required=False)
    adjustment_entries = AdjustmentEntrySerializer(many=True, required=False)

    class Meta:
        model = Part
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
            "time_entries",
            "material_entries",
            "adjustment_entries",
        ]
        read_only_fields = ["created_at", "updated_at"]
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert UUID id field to string for JSON serialization
        representation['id'] = str(representation['id'])
        
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
        
        return representation

    def create(self, validated_data):
        # Extract nested entry data
        time_entries_data = validated_data.pop('time_entries', [])
        material_entries_data = validated_data.pop('material_entries', [])
        adjustment_entries_data = validated_data.pop('adjustment_entries', [])
        
        # Create the part
        part = Part.objects.create(**validated_data)
        
        # Create nested entries
        for time_entry_data in time_entries_data:
            time_entry_data['part'] = part
            time_serializer = TimeEntrySerializer(data=time_entry_data)
            if time_serializer.is_valid():
                time_serializer.save()
            else:
                raise serializers.ValidationError({"time_entries": time_serializer.errors})
            
        for material_entry_data in material_entries_data:
            material_entry_data['part'] = part
            material_serializer = MaterialEntrySerializer(data=material_entry_data)
            if material_serializer.is_valid():
                material_serializer.save()
            else:
                raise serializers.ValidationError({"material_entries": material_serializer.errors})
            
        for adjustment_entry_data in adjustment_entries_data:
            adjustment_entry_data['part'] = part
            adjustment_serializer = AdjustmentEntrySerializer(data=adjustment_entry_data)
            if adjustment_serializer.is_valid():
                adjustment_serializer.save()
            else:
                raise serializers.ValidationError({"adjustment_entries": adjustment_serializer.errors})
            
        return part

    def update(self, instance, validated_data):
        # Extract nested entry data
        time_entries_data = validated_data.pop('time_entries', [])
        material_entries_data = validated_data.pop('material_entries', [])
        adjustment_entries_data = validated_data.pop('adjustment_entries', [])
        
        # Update part fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update time entries
        if time_entries_data is not None:
            instance.time_entries.all().delete()
            for time_entry_data in time_entries_data:
                time_entry_data['part'] = instance
                time_serializer = TimeEntrySerializer(data=time_entry_data)
                if time_serializer.is_valid():
                    time_serializer.save()
                else:
                    raise serializers.ValidationError({"time_entries": time_serializer.errors})
                
        # Update material entries
        if material_entries_data is not None:
            instance.material_entries.all().delete()
            for material_entry_data in material_entries_data:
                material_entry_data['part'] = instance
                material_serializer = MaterialEntrySerializer(data=material_entry_data)
                if material_serializer.is_valid():
                    material_serializer.save()
                else:
                    raise serializers.ValidationError({"material_entries": material_serializer.errors})
                
        # Update adjustment entries
        if adjustment_entries_data is not None:
            instance.adjustment_entries.all().delete()
            for adjustment_entry_data in adjustment_entries_data:
                adjustment_entry_data['part'] = instance
                adjustment_serializer = AdjustmentEntrySerializer(data=adjustment_entry_data)
                if adjustment_serializer.is_valid():
                    adjustment_serializer.save()
                else:
                    raise serializers.ValidationError({"adjustment_entries": adjustment_serializer.errors})
                
        return instance