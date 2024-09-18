import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html

from workflow.models import Client


class ClientTable(tables.Table):
    edit = tables.Column(empty_values=(), orderable=False)

    class Meta:
        model = Client
        template_code = (
            '<a href="{% url "update-client" record.pk %}" class="btn btn-sm btn-primary">Edit</a>',
        )
        template_name = (
            "django_tables2/bootstrap4.html"  # You can choose other templates
        )
        fields = ("name", "email", "phone", "address", "is_account_customer", "edit")

    def render_edit(self, value, record):
        edit_url = reverse(
            "update_client", args=[record.pk]
        )  # Note the changed URL name
        return format_html(
            '<a href="{}" class="btn btn-sm btn-primary">Edit</a>', edit_url
        )