from timesheet.models import TimeEntry as TimesheetEntry


class TimeEntry(TimesheetEntry):
    """
    Proxy model for Timesheet to maintain compatibility with existing code.
    This allows the code to continue referencing workflow.TimeEntry while
    the actual model is now in timesheet.TimeEntry.
    """

    class Meta:
        proxy = True
        app_label = "workflow"

