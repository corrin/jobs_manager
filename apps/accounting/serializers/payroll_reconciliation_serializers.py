"""Serializers for the payroll reconciliation report API."""

from typing import Any

from rest_framework import serializers


class PayrollStaffWeekSerializer(serializers.Serializer[Any]):
    """Per-staff row within a single reconciliation week."""

    name = serializers.CharField()
    xero_hours = serializers.FloatField()
    xero_timesheet_hours = serializers.FloatField()
    xero_leave_hours = serializers.FloatField()
    xero_gross = serializers.FloatField()
    xero_rate = serializers.FloatField()
    jm_hours = serializers.FloatField()
    jm_cost = serializers.FloatField()
    jm_rate = serializers.FloatField()
    hours_diff = serializers.FloatField()
    cost_diff = serializers.FloatField()
    hours_cost_impact = serializers.FloatField()
    rate_cost_impact = serializers.FloatField()
    status = serializers.CharField()


class PayrollWeekTotalsSerializer(serializers.Serializer[Any]):
    """Aggregate totals for a single reconciliation week."""

    xero_gross = serializers.FloatField()
    jm_cost = serializers.FloatField()
    diff = serializers.FloatField()
    xero_hours = serializers.FloatField()
    jm_hours = serializers.FloatField()


class PayrollWeekSerializer(serializers.Serializer[Any]):
    """One week of reconciliation data (pay run vs JM CostLines)."""

    week_start = serializers.DateField()
    xero_period_start = serializers.DateField()
    xero_period_end = serializers.DateField()
    payment_date = serializers.DateField()
    totals = PayrollWeekTotalsSerializer()
    mismatch_count = serializers.IntegerField()
    staff = PayrollStaffWeekSerializer(many=True)


class PayrollStaffSummarySerializer(serializers.Serializer[Any]):
    """Per-staff aggregate across all weeks in the reporting window."""

    name = serializers.CharField()
    xero_hours = serializers.FloatField()
    xero_gross = serializers.FloatField()
    jm_hours = serializers.FloatField()
    jm_cost = serializers.FloatField()
    hours_diff = serializers.FloatField()
    cost_diff = serializers.FloatField()
    hours_cost_impact = serializers.FloatField()
    rate_cost_impact = serializers.FloatField()
    weeks_present = serializers.IntegerField()
    weeks_with_mismatch = serializers.IntegerField()


class PayrollHeatmapRowSerializer(serializers.Serializer[Any]):
    """Single row in the heatmap grid (one week)."""

    week_start = serializers.DateField()
    cells = serializers.DictField(child=serializers.FloatField(allow_null=True))


class PayrollHeatmapSerializer(serializers.Serializer[Any]):
    """Week x staff cost-difference heatmap."""

    staff_names = serializers.ListField(child=serializers.CharField())
    rows = PayrollHeatmapRowSerializer(many=True)


class PayrollGrandTotalsSerializer(serializers.Serializer[Any]):
    """Grand totals across all weeks in the reporting window."""

    xero_gross = serializers.FloatField()
    jm_cost = serializers.FloatField()
    diff = serializers.FloatField()
    diff_pct = serializers.FloatField()


class PayrollReconciliationResponseSerializer(serializers.Serializer[Any]):
    """Top-level response for the payroll reconciliation API."""

    weeks = PayrollWeekSerializer(many=True)
    staff_summaries = PayrollStaffSummarySerializer(many=True)
    heatmap = PayrollHeatmapSerializer()
    grand_totals = PayrollGrandTotalsSerializer()
