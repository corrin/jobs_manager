from django.urls import reverse
from rest_framework import serializers

from apps.job.models import JobFile


class JobFileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = JobFile
        fields = [
            "id",
            "filename",
            "size",
            "mime_type",
            "uploaded_at",
            "print_on_jobsheet",
            "download_url",
            "thumbnail_url",
            "status",
        ]

    def get_download_url(self, obj: JobFile):
        request = self.context["request"]
        path = reverse("jobs:job_file_download", args=[obj.file_path])
        return request.build_absolute_uri(path)

    def get_thumbnail_url(self, obj: JobFile):
        if not obj.thumbnail_path:
            return None
        request = self.context["request"]
        path = reverse("jobs:job_file_thumbnail", args=[str(obj.id)])
        return request.build_absolute_uri(path)


class UploadedFileSerializer(serializers.Serializer):
    """Serializer for file upload response."""

    id = serializers.CharField()
    filename = serializers.CharField()
    file_path = serializers.CharField()
    print_on_jobsheet = serializers.BooleanField()


class JobFileUploadSuccessResponseSerializer(serializers.Serializer):
    """Serializer for successful file upload response."""

    status = serializers.CharField(default="success")
    uploaded = UploadedFileSerializer(many=True)
    message = serializers.CharField()


class JobFileUploadPartialResponseSerializer(serializers.Serializer):
    """Serializer for partial success file upload response."""

    status = serializers.CharField()
    uploaded = UploadedFileSerializer(many=True)
    errors = serializers.ListField(child=serializers.CharField())


class JobFileErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""

    status = serializers.CharField(default="error")
    message = serializers.CharField()


class JobFileUpdateSuccessResponseSerializer(serializers.Serializer):
    """Serializer for successful file update response."""

    status = serializers.CharField(default="success")
    message = serializers.CharField()
    print_on_jobsheet = serializers.BooleanField()


class JobFileThumbnailErrorResponseSerializer(serializers.Serializer):
    """Serializer for thumbnail error response."""

    status = serializers.CharField(default="error")
    message = serializers.CharField()


class JobFileUploadViewResponseSerializer(serializers.Serializer):
    """Serializer for JobFileUploadView response."""

    status = serializers.CharField(default="success")
    uploaded = JobFileSerializer(many=True)
    message = serializers.CharField()
