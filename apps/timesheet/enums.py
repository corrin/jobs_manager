from decimal import Decimal

from django.db import models


class RateType(models.TextChoices):
    """
    Types of pay rates for job time entries
    """

    ORDINARY = "Ord", "Ordinary Time"
    TIME_AND_HALF = "1.5", "Time and a Half"
    DOUBLE_TIME = "2.0", "Double Time"
    UNPAID = "Unpaid", "Unpaid"

    @property
    def multiplier(self) -> Decimal:
        multipliers: dict[str, Decimal] = {
            RateType.ORDINARY.value: Decimal("1.0"),
            RateType.TIME_AND_HALF.value: Decimal("1.5"),
            RateType.DOUBLE_TIME.value: Decimal("2.0"),
            RateType.UNPAID.value: Decimal("0.0"),
        }
        return multipliers[self.value]
