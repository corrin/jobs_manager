from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.job.models import CostLine, CostSet, Job


class CostLineSchemaValidationTests(TestCase):
    def setUp(self) -> None:
        self.job = Job.objects.create(
            job_number=1,
            name="CostLine Schema Test",
            charge_out_rate=Decimal("120.00"),
        )
        self.cost_set = CostSet.objects.create(job=self.job, kind="actual", rev=1)

    def _build_cost_line(self, **overrides) -> CostLine:
        base_kwargs = {
            "cost_set": self.cost_set,
            "kind": "time",
            "desc": "Schema test line",
            "quantity": Decimal("1.000"),
            "unit_cost": Decimal("10.00"),
            "unit_rev": Decimal("15.00"),
            "accounting_date": date.today(),
            "meta": {},
            "ext_refs": {},
        }
        base_kwargs.update(overrides)
        return CostLine(**base_kwargs)

    def test_time_meta_allows_known_keys(self) -> None:
        meta = {
            "staff_id": str(uuid4()),
            "date": date.today().isoformat(),
            "is_billable": True,
            "rate_multiplier": 1.5,
            "wage_rate": Decimal("45.00"),
            "charge_out_rate": Decimal("90.00"),
        }
        line = self._build_cost_line(meta=meta)
        # Should not raise ValidationError
        line.full_clean()

    def test_meta_rejects_unknown_keys(self) -> None:
        line = self._build_cost_line(
            meta={"staff_id": str(uuid4()), "unexpected": "value"}
        )
        with self.assertRaises(ValidationError) as exc:
            line.full_clean()
        self.assertIn("meta", exc.exception.message_dict)

    def test_ext_refs_reject_unknown_keys(self) -> None:
        line = self._build_cost_line(ext_refs={"experiment": "value"})
        with self.assertRaises(ValidationError) as exc:
            line.full_clean()
        self.assertIn("ext_refs", exc.exception.message_dict)

    def test_save_invokes_schema_validation(self) -> None:
        line = self._build_cost_line(
            meta={"staff_id": str(uuid4()), "unknown_field": "value"}
        )
        with self.assertRaises(ValidationError):
            line.save()
