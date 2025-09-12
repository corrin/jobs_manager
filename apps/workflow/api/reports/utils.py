import calendar


def format_period_label(period_start, period_end):
    """
    Format a date range into a human-readable label.

    Args:
        period_start: Start date of the period
        period_end: End date of the period

    Returns:
        str: Formatted label based on the date range pattern
    """
    # If it's a single day
    if period_start == period_end:
        return period_start.strftime("%d %b %Y")

    # If it's a whole month (1st to last day)
    if (
        period_start.day == 1
        and period_end.day == calendar.monthrange(period_end.year, period_end.month)[1]
    ):
        return period_start.strftime("%b %Y")

    # If it's a fiscal year (assuming April 1 to March 31)
    if (
        period_start.month == 4
        and period_start.day == 1
        and period_end.month == 3
        and period_end.day == 31
    ):
        return f"FY {period_end.year}"

    # Otherwise show date range
    return f"{period_start.strftime('%d %b %Y')} - {period_end.strftime('%d %b %Y')}"
