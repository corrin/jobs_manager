from zoneinfo import ZoneInfo


def get_nz_tz() -> ZoneInfo:
    """
    Gets the New Zealand timezone object using zoneinfo.

    Returns:
        ZoneInfo: A timezone object for Pacific/Auckland
    """
    return ZoneInfo("Pacific/Auckland")
