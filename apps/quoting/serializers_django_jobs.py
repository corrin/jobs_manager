from django_apscheduler.models import DjangoJob, DjangoJobExecution
from rest_framework import serializers


class DjangoJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DjangoJob
        fields = [
            "id",
            "next_run_time",
            "job_state",
        ]


class DjangoJobExecutionSerializer(serializers.ModelSerializer):
    job_id = serializers.CharField(source="job.id", read_only=True)

    class Meta:
        model = DjangoJobExecution
        fields = [
            "id",
            "job_id",
            "status",
            "run_time",
            "duration",
            "exception",
            "traceback",
        ]
