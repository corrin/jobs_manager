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
