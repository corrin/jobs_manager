from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Literal

Kind = Literal["time", "material", "adjust"]


@dataclass
class DraftLine:
    kind: Kind
    desc: str
    quantity: Decimal = Decimal("1")
    unit_cost: Decimal = Decimal("0")
    unit_rev: Decimal = Decimal("0")
    meta: Dict[str, str] = field(default_factory=dict)
    source_row: int | None = None
    source_sheet: str | None = None

    @property
    def total_cost(self) -> Decimal:
        return (self.quantity * self.unit_cost).quantize(Decimal("0.01"))

    @property
    def total_rev(self) -> Decimal:
        return (self.quantity * self.unit_rev).quantize(Decimal("0.01"))
