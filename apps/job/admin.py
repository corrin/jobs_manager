from django.contrib import admin

from apps.job.models import CostLine, CostSet


class CostLineInline(admin.TabularInline):
    model = CostLine
    extra = 0
    fields = ("kind", "desc", "quantity", "unit_cost", "unit_rev")
    readonly_fields = ("total_cost", "total_rev")


@admin.register(CostSet)
class CostSetAdmin(admin.ModelAdmin):
    list_display = ("job", "kind", "rev", "created")
    list_filter = ("kind", "created")
    search_fields = ("job__name",)
    inlines = [CostLineInline]
    readonly_fields = ("created",)

    fieldsets = (
        (None, {"fields": ("job", "kind", "rev")}),
        ("Metadata", {"fields": ("summary", "created"), "classes": ("collapse",)}),
    )


@admin.register(CostLine)
class CostLineAdmin(admin.ModelAdmin):
    list_display = (
        "cost_set",
        "kind",
        "desc",
        "quantity",
        "unit_cost",
        "unit_rev",
        "total_cost",
        "total_rev",
    )
    list_filter = ("kind", "cost_set__kind", "cost_set__job")
    search_fields = ("desc", "cost_set__job__name")
    readonly_fields = ("total_cost", "total_rev")

    fieldsets = (
        (None, {"fields": ("cost_set", "kind", "desc")}),
        ("Costing", {"fields": ("quantity", "unit_cost", "unit_rev")}),
        ("Metadata", {"fields": ("ext_refs", "meta"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("cost_set__job")
