from decimal import Decimal

import pytest
from django.utils import timezone

from apps.client.models import Client
from apps.job.models import Job
from apps.workflow.models import CompanyDefaults


@pytest.fixture
def job(db):
    CompanyDefaults.objects.get_or_create(
        defaults={"charge_out_rate": Decimal("105.00")}
    )
    client = Client.objects.create(
        name="Test Client",
        xero_last_modified=timezone.now(),
    )
    return Job.objects.create(client=client, name="Test Job")
