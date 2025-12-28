import decimal
import json
from decimal import Decimal
from typing import Any, Union


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def decimal_to_float(value: Union[Decimal, Any]) -> Union[float, Any]:
    return float(value) if isinstance(value, Decimal) else value
