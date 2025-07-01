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
        multipliers = {
            self.ORDINARY: Decimal("1.0"),
            self.TIME_AND_HALF: Decimal("1.5"),
            self.DOUBLE_TIME: Decimal("2.0"),
            self.UNPAID: Decimal("0.0"),
        }
        return multipliers[self]
