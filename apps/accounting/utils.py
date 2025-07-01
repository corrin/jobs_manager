from datetime import timezone
from zoneinfo import ZoneInfo


def get_nz_tz() -> timezone | ZoneInfo:
    """
    Gets the New Zealand timezone object using either zoneinfo or pytz.

    Returns:
        timezone | ZoneInfo: A timezone object for Pacific/Auckland,
        using ZoneInfo if available (Python 3.9+) or falling back to pytz
    """
    try:
        from zoneinfo import ZoneInfo

        nz_timezone = ZoneInfo("Pacific/Auckland")
    except ImportError:
        import pytz

        nz_timezone = pytz.timezone("Pacific/Auckland")
    return nz_timezone
