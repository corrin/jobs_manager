from decimal import Decimal
from typing import Optional

import pandas as pd
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.job.enums import JobPricingStage
from apps.job.models import AdjustmentEntry, Job, JobPart, JobPricing, MaterialEntry

MANDATORY_COLUMNS = [
    "description",
    "quantity",
    "thickness",
    "materials",
    "labor / laser (internal)",
    "bend cost",
    "bend setup fee",
    "hole cost",
    "weld cost",
    "material cost",
    "pipe (rhs/shs/pipe)",
    "preparation (detail/finish)",
    "clear",
]

ADJUSTMENT_COLUMNS = [
    "bend cost",
    "bend setup fee",
    "hole cost",
    "weld cost",
    "pipe (rhs/shs/pipe)",
    "preparation (detail/finish)",
]

COLUMN_ALIASES = {
    "labour /laser (inhouse)": "labor / laser (internal)",
    "fold cost": "bend cost",
    "fold set up fee": "bend setup fee",
    "hole costs": "hole cost",
    "welding cost": "weld cost",
    "materials cost": "material cost",
    "tube (rhs/shs/pipe)": "pipe (rhs/shs/pipe)",
    "prep (detail/finish)": "preparation (detail/finish)",
}


def _clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns.str.strip().str.replace(r"\s+", " ", regex=True).str.lower()
    )
    df.rename(columns=COLUMN_ALIASES, inplace=True)
    return df


@transaction.atomic
def import_quote_from_excel(
    *, job: Job, file, job_pricing_id: Optional[str] = None
) -> dict:
    """Create JobParts from a spreadsheet and return summary."""

    xl = pd.ExcelFile(file, engine="openpyxl")

    try:
        df = xl.parse("Primary Details")
    except ValueError as exc:
        raise ValidationError("Missing 'Primary Details' sheet") from exc

    df = _clean_cols(df)

    missing_cols = [c for c in MANDATORY_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValidationError(f"Missing mandatory columns: {', '.join(missing_cols)}")

    # Validate materials sheet
    try:
        materials_df = xl.parse("Materials")
    except ValueError:
        raise ValidationError("Missing 'Materials' sheet")

    materials_df = _clean_cols(materials_df)

    for col in ["thickness", "materials"]:
        if col not in materials_df.columns:
            raise ValidationError(f"Materials sheet missing '{col}' column")

    valid_thickness = set(str(x) for x in materials_df["thickness"].dropna())
    valid_materials = set(str(x) for x in materials_df["materials"].dropna())

    # Determine job pricing
    job_pricing: Optional[JobPricing] = None
    if job_pricing_id:
        try:
            job_pricing = JobPricing.objects.get(id=job_pricing_id, job=job)
        except JobPricing.DoesNotExist as exc:
            raise ValidationError("Invalid job_pricing_id") from exc
    else:
        job_pricing = job.pricings.filter(
            pricing_stage=JobPricingStage.ESTIMATE
        ).first()
        if job_pricing is None:
            job_pricing = JobPricing.objects.create(
                job=job, pricing_stage=JobPricingStage.ESTIMATE
            )
            job.latest_estimate_pricing = job_pricing
            job.save(update_fields=["latest_estimate_pricing"])

    parts_created = 0
    total_material_cost = Decimal("0")
    total_adjustments_cost = Decimal("0")

    for _, row in df.iterrows():
        description = str(row.get("description", "")).strip()
        clear_val = str(row.get("clear", "")).strip().upper()
        if not description or clear_val == "CLEAR":
            continue

        quantity = Decimal(str(row.get("quantity", 0)))
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero")

        thickness_val = str(row.get("thickness", ""))
        material_val = str(row.get("materials", ""))
        if thickness_val not in valid_thickness or material_val not in valid_materials:
            raise ValidationError("Invalid thickness or material")

        part = JobPart.objects.create(
            job_pricing=job_pricing,
            name=description,
            description=description,
        )

        material_cost = Decimal(str(row.get("material cost", 0)))
        unit_cost = material_cost / quantity if quantity else Decimal("0")

        MaterialEntry.objects.create(
            job_pricing=job_pricing,
            description=material_val,
            comments=f"{thickness_val}mm {material_val}",
            quantity=quantity,
            unit_cost=unit_cost,
            unit_revenue=unit_cost,
        )

        adjustments_total = Decimal("0")
        for col in ADJUSTMENT_COLUMNS:
            value = Decimal(str(row.get(col, 0)))
            if value != 0:
                AdjustmentEntry.objects.create(
                    job_pricing=job_pricing,
                    description=col,
                    cost_adjustment=value,
                    price_adjustment=Decimal("0"),
                )
                adjustments_total += value

        labor_cost = Decimal(str(row.get("labor / laser (internal)", 0)))

        part.raw_total_cost = material_cost + adjustments_total + labor_cost

        parts_created += 1
        total_material_cost += material_cost
        total_adjustments_cost += adjustments_total

    return {
        "job_pricing_id": str(job_pricing.id),
        "partes_criadas": parts_created,
        "total_material_cost": str(total_material_cost),
        "total_adjustments_cost": str(total_adjustments_cost),
    }
