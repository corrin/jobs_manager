import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from apps.job.services.delta_checksum import compute_job_delta_checksum


def test_checksum_is_deterministic_with_sorted_fields():
    job_id = uuid.uuid4()
    values = {"description": "Cut and fold", "order_number": "PO-123"}

    checksum_a = compute_job_delta_checksum(job_id, values)
    checksum_b = compute_job_delta_checksum(job_id, dict(reversed(values.items())))

    assert checksum_a == checksum_b


def test_checksum_trims_strings_and_normalises_null():
    job_id = "job-123"
    values = {"description": "  padded  ", "notes": None}

    checksum = compute_job_delta_checksum(job_id, values)
    assert checksum == compute_job_delta_checksum(
        job_id, {"description": "padded", "notes": None}
    )


def test_checksum_handles_decimal_and_boolean_and_numbers():
    job_id = "job-123"
    values = {
        "charge_out_rate": Decimal("5.10"),
        "priority": 3,
        "flagged": True,
    }

    checksum = compute_job_delta_checksum(job_id, values)
    assert checksum == compute_job_delta_checksum(
        job_id,
        {"charge_out_rate": Decimal("5.100"), "priority": 3, "flagged": True},
    )


def test_checksum_handles_datetimes_and_dates():
    job_id = "job-123"
    dt = datetime(2025, 10, 7, 8, 7, 11, 251000, tzinfo=timezone.utc)
    d = date(2025, 10, 7)

    checksum = compute_job_delta_checksum(job_id, {"updated_at": dt, "delivery": d})

    naive_dt = dt.replace(tzinfo=None)
    assert checksum == compute_job_delta_checksum(
        job_id, {"updated_at": naive_dt, "delivery": d}
    )


def test_checksum_respects_explicit_field_subset():
    job_id = "job-123"
    values = {
        "name": "Part A",
        "description": "Cut and fold",
        "notes": "Internal",
    }

    checksum_all = compute_job_delta_checksum(job_id, values)
    checksum_subset = compute_job_delta_checksum(job_id, values, fields=["description"])

    assert checksum_all != checksum_subset


def test_checksum_raises_when_job_id_missing():
    with pytest.raises(ValueError):
        compute_job_delta_checksum("", {"name": "Part A"})


def test_checksum_raises_for_missing_field_in_subset():
    with pytest.raises(ValueError):
        compute_job_delta_checksum("job-1", {"name": "Part A"}, fields=["description"])
