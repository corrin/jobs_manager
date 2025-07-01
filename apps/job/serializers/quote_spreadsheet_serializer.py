"""
Quote Spreadsheet Serializer

Serializer for QuoteSpreadsheet model, providing clean JSON representation
for REST API endpoints.
"""

from rest_framework import serializers

from apps.job.models.spreadsheet import QuoteSpreadsheet


class QuoteSpreadsheetSerializer(serializers.ModelSerializer):
    """
    Serializer for QuoteSpreadsheet model.

    Provides clean JSON representation for REST endpoints with
    job information for context.
    """

    job_id = serializers.CharField(source="job.id", read_only=True)
    job_number = serializers.CharField(source="job.job_number", read_only=True)
    job_name = serializers.CharField(source="job.name", read_only=True)

    class Meta:
        model = QuoteSpreadsheet
        fields = [
            "id",
            "sheet_id",
            "sheet_url",
            "tab",
            "job_id",
            "job_number",
            "job_name",
        ]
        read_only_fields = ["id", "job_id", "job_number", "job_name"]
