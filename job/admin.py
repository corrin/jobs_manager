from django.contrib import admin
from job.models import Part, MaterialEntry, AdjustmentEntry

# Register your models here.
@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ('name', 'job_pricing', 'created_at', 'updated_at')
    list_filter = ('job_pricing__pricing_type',)
    search_fields = ('name', 'description', 'job_pricing__job__name')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('job_pricing', 'job_pricing__job')
