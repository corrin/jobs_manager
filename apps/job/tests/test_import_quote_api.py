import io

import pandas as pd
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.job.models import Job


@pytest.fixture
def staff(db):
    User = get_user_model()
    return User.objects.create_user(email="staff@example.com", password="testpass")


@pytest.fixture
def client_logged(client, staff):
    client.force_login(staff)
    return client


def create_excel(quantity=1, include_description=True, extra_cols=None):
    data = {
        "quantity": [quantity],
        "Description": ["Part A" if include_description else ""],
        "Labour /laser (inhouse)": [90],
        "thickness": [1.5],
        "Materials": ["SS316"],
        "fold cost": [9],
        "fold set up fee": [10],
        "hole costs": [15],
        "welding cost": [48],
        "Materials cost": [276.5],
        "Tube (RHS/SHS/pipe)": [12.0],
        "Prep (detail/finish)": [30],
        "CLEAR": [""],
    }
    if extra_cols:
        data.update(extra_cols)
    df_primary = pd.DataFrame(data)
    materials_df = pd.DataFrame({"thickness": [1.5], "Materials": ["SS316"]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_primary.to_excel(writer, sheet_name="Primary Details", index=False)
        materials_df.to_excel(writer, sheet_name="Materials", index=False)
    buf.seek(0)
    return buf


@pytest.fixture
def job(db, staff):
    job = Job(name="Test", charge_out_rate=1)
    job.save(staff=staff)
    return job


def test_upload_valid_spreadsheet(client_logged, job):
    file = create_excel()
    url = reverse("jobs:import_quote", args=[job.id])
    response = client_logged.post(url, {"file": file})
    assert response.status_code == 200
    data = response.json()
    assert data["partes_criadas"] == 1


def test_missing_columns(client_logged, job):
    file = create_excel()
    # remove a mandatory column
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame({"foo": [1]}).to_excel(
            writer, sheet_name="Primary Details", index=False
        )
        pd.DataFrame({"thickness": [1.5], "Materials": ["SS316"]}).to_excel(
            writer, sheet_name="Materials", index=False
        )
    buf.seek(0)
    url = reverse("jobs:import_quote", args=[job.id])
    response = client_logged.post(url, {"file": buf})
    assert response.status_code == 400


def test_quantity_zero_error(client_logged, job):
    file = create_excel(quantity=0)
    url = reverse("jobs:import_quote", args=[job.id])
    response = client_logged.post(url, {"file": file})
    assert response.status_code == 400
