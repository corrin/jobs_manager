import json

import io

import base64

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.html import format_html
from django.contrib import messages
from django.views.generic import TemplateView
from decimal import Decimal

from workflow.models import Job, JobPricing, Staff, TimeEntry
from workflow.forms import PaidAbsenceForm
from workflow.utils import extract_messages

import logging
from django.template.loader import render_to_string

# Configure logging to only show logs from this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Disable matplotlib debug logging without affecting other loggers
logging.getLogger("matplotlib").propagate = False


# Excluding app users ID's to avoid them being loaded in timesheet views because they do not have entries
# (Valerie and Corrin included as they are not supposed to enter hours)
EXCLUDED_STAFF_IDS = [
    "a9bd99fa-c9fb-43e3-8b25-578c35b56fa6",
    "b50dd08a-58ce-4a6c-b41e-c3b71ed1d402",
    "d335acd4-800e-517a-8ff4-ba7aada58d14",
    "e61e2723-26e1-5d5a-bd42-bbd318ddef81",
]

# This way we make only one query to the database for both views, which saves resources and improves the performance
filtered_staff = [
    staff_member
    for staff_member in sorted(
        Staff.objects.all(), key=lambda x: x.get_display_full_name()
    )
    if not (staff_member.is_staff is True or str(staff_member.id) in EXCLUDED_STAFF_IDS)
]


class TimesheetOverviewView(TemplateView):
    """View for displaying timesheet overview including staff hours, job statistics and graphics."""

    template_name = "time_entries/timesheet_overview.html"

    def get(self, request, start_date=None, *args, **kwargs):
        """Handle GET request to display timesheet overview.

        Args:
            request: The HTTP request
            start_date: Optional start date string in YYYY-MM-DD format

        Returns:
            Rendered template with timesheet data context
        """
        try:
            start_date = self._get_start_date(start_date)
            week_days = self._get_week_days(start_date)
            staff_data, totals = self._get_staff_data(week_days)
            graphic_html = self._generate_graphic()

            context = {
                "week_days": week_days,
                "staff_data": staff_data,
                "weekly_summary": self._format_weekly_summary(totals),
                "job_count": self._get_open_jobs().count(),
                "graphic": graphic_html,
            }

            return render(request, self.template_name, context)
        except Exception as e:
            logger.error(f"Error in TimesheetOverviewView.get: {str(e)}")
            messages.error(
                request, "An error occurred while loading the timesheet overview."
            )
            return render(request, self.template_name, {"error": True})

    def _get_open_jobs(self):
        """Get all open jobs with relevant statuses.

        Returns:
            QuerySet of Job objects or empty QuerySet on error
        """
        try:
            return Job.objects.filter(
                status__in=["quoting", "approved", "in_progress", "special"]
            )
        except Exception as e:
            logger.error(f"Error getting open jobs: {str(e)}")
            return Job.objects.none()

    def _get_start_date(self, start_date):
        """Parse and validate the start date.

        Args:
            start_date: Date string in YYYY-MM-DD format

        Returns:
            datetime.date object for start date or default date 7 days ago
        """
        if start_date:
            try:
                return datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError as e:
                logger.warning(f"Invalid start date format: {str(e)}")
                return timezone.now().date() - timezone.timedelta(days=7)
        return timezone.now().date() - timezone.timedelta(days=7)

    def _get_week_days(self, start_date):
        """Generate list of weekdays from start date.

        Args:
            start_date: datetime.date object for start of week

        Returns:
            List of datetime.date objects for weekdays
        """
        try:
            return [
                start_date + timezone.timedelta(days=i)
                for i in range(-start_date.weekday(), 5 - start_date.weekday())
            ]
        except Exception as e:
            logger.error(f"Error generating week days: {str(e)}")
            return []

    def _get_staff_data(self, week_days):
        """Get timesheet data for all staff members.

        Args:
            week_days: List of datetime.date objects for the week

        Returns:
            Tuple of (staff_data list, totals dict)
        """
        staff_data = []
        total_hours = 0
        total_billable_hours = 0

        try:
            for staff_member in filtered_staff:
                weekly_hours = []
                total_staff_hours = 0
                billable_hours = 0

                for day in week_days:
                    try:
                        daily_data = self._get_daily_data(staff_member, day)
                        weekly_hours.append(daily_data["daily_summary"])
                        total_staff_hours += daily_data["hours"]
                        billable_hours += daily_data["billable_hours"]
                    except Exception as e:
                        logger.error(
                            f"Error processing daily data for {staff_member} on {day}: {str(e)}"
                        )
                        weekly_hours.append({"day": day, "hours": 0, "status": "⚠"})

                staff_data.append(
                    {
                        "staff_id": staff_member.id,
                        "name": staff_member.get_display_full_name(),
                        "weekly_hours": weekly_hours,
                        "total_hours": total_staff_hours,
                        "billable_percentage": self._calculate_percentage(
                            billable_hours, total_staff_hours
                        ),
                    }
                )

                total_hours += total_staff_hours
                total_billable_hours += billable_hours

            return staff_data, {
                "total_hours": total_hours,
                "billable_percentage": self._calculate_percentage(
                    total_billable_hours, total_hours
                ),
            }
        except Exception as e:
            logger.error(f"Error processing staff data: {str(e)}")
            return [], {"total_hours": 0, "billable_percentage": 0}

    def _get_daily_data(self, staff_member, day):
        """Get timesheet data for a staff member on a specific day.

        Args:
            staff_member: Staff object
            day: datetime.date object

        Returns:
            Dict containing hours, billable hours and daily summary
        """
        try:
            scheduled_hours = staff_member.get_scheduled_hours(day)
            time_entries = TimeEntry.objects.filter(
                staff=staff_member, date=day
            ).select_related("job_pricing")

            daily_hours = sum(entry.hours for entry in time_entries)
            daily_billable_hours = sum(
                entry.hours for entry in time_entries if entry.is_billable
            )
            has_paid_leave = time_entries.filter(
                job_pricing__job__name__icontains="Leave"
            ).exists()

            return {
                "hours": daily_hours,
                "billable_hours": daily_billable_hours,
                "daily_summary": {
                    "day": day,
                    "hours": daily_hours,
                    "status": self._get_status(
                        daily_hours, scheduled_hours, has_paid_leave
                    ),
                },
            }
        except Exception as e:
            logger.error(
                f"Error getting daily data for {staff_member} on {day}: {str(e)}"
            )
            return {
                "hours": 0,
                "billable_hours": 0,
                "daily_summary": {"day": day, "hours": 0, "status": "⚠"},
            }

    def _get_status(self, daily_hours, scheduled_hours, has_paid_leave):
        """Determine status indicator for a day's hours.

        Args:
            daily_hours: Total hours worked
            scheduled_hours: Expected hours
            has_paid_leave: Whether paid leave was taken

        Returns:
            Status indicator string
        """
        try:
            if has_paid_leave:
                return "Leave"
            return "✓" if daily_hours >= scheduled_hours else "⚠"
        except Exception as e:
            logger.error(f"Error determining status: {str(e)}")
            return "⚠"

    def _format_weekly_summary(self, totals):
        """Format weekly totals for display.

        Args:
            totals: Dict containing total_hours and billable_percentage

        Returns:
            Formatted totals dict
        """
        try:
            return {
                "total_hours": totals["total_hours"],
                "billable_percentage": round(totals["billable_percentage"], 1),
            }
        except Exception as e:
            logger.error(f"Error formatting weekly summary: {str(e)}")
            return {"total_hours": 0, "billable_percentage": 0}

    def _generate_graphic(self):
        """Generate bar chart comparing estimated vs actual hours for jobs.

        Returns:
            HTML string containing base64 encoded PNG image
        """
        try:
            open_jobs = self._get_open_jobs()

            job_names = [job.name for job in open_jobs]

            estimated_hours = [
                (
                    job.latest_estimate_pricing.total_hours
                    if job.latest_estimate_pricing
                    else 0
                )
                for job in open_jobs
            ]

            actual_hours = [
                (
                    job.latest_reality_pricing.total_hours
                    if job.latest_reality_pricing
                    else 0
                )
                for job in open_jobs
            ]

            fig, ax = plt.subplots(figsize=(8, 4))

            job_names = [
                name[:20] + "..." if len(name) > 20 else name for name in job_names
            ]

            bar_width = 0.3
            x_positions = range(len(job_names))

            ax.bar(
                x_positions,
                estimated_hours,
                width=bar_width,
                label="Estimated Hours",
                color="blue",
            )
            ax.bar(
                [x + bar_width for x in x_positions],
                actual_hours,
                width=bar_width,
                label="Actual Hours",
                color="orange",
            )

            ax.set_title("Comparison of Estimated vs Actual Hours")
            ax.set_xticks([x + bar_width / 2 for x in x_positions])
            ax.set_xticklabels(job_names, rotation=45, ha="right")

            ax.yaxis.grid(True, linestyle="--", alpha=0.7)
            ax.set_axisbelow(True)

            ax.legend()
            plt.tight_layout()

            buffer = io.BytesIO()
            plt.savefig(buffer, format="png")
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()

            return format_html(
                '<img src="data:image/png;base64,{}"/>',
                base64.b64encode(image_png).decode("utf-8"),
            )
        except Exception as e:
            logger.error(f"Error generating graphic: {str(e)}")
            return format_html('<p class="error">Error generating chart</p>')

    def _calculate_percentage(self, part, total):
        """Calculate percentage with rounding.

        Args:
            part: Numerator value
            total: Denominator value

        Returns:
            Rounded percentage value
        """
        return round((part / total) * 100, 1) if total > 0 else 0

    def post(self, request, *args, **kwargs):
        """Handle POST requests for paid absence actions.

        Args:
            request: The HTTP request

        Returns:
            JsonResponse with result or error
        """
        action = request.POST.get("action")
        if action == "load_paid_absence_form":
            return self.load_paid_absence_form(request)
        if action == "submit_paid_absence":
            return self.submit_paid_absence(request)
        messages.error(request, "Invalid action.")
        return JsonResponse(
            {"error": "Invalid action.", "messages": extract_messages(request)},
            status=400,
        )

    def load_paid_absence_form(self, request):
        """Load and return the paid absence form.

        Args:
            request: The HTTP request

        Returns:
            Form HTML
        """
        form = PaidAbsenceForm()
        form_html = render_to_string(
            "time_entries/paid_absence_form.html",
            {"form": form, "staff_members": filtered_staff},
            request=request,
        )
        return JsonResponse(
            {
                "form_html": form_html,
                "success": True,
            }
        )

    def submit_paid_absence(self, request):
        """Handle submission of paid absence form and create leave entries.

        Creates TimeEntry records for each weekday in the date range with the specified
        leave type. Skips weekends and validates form data.

        Args:
            request: The HTTP request containing form data

        Returns:
            JsonResponse with success/error status and messages

        Form Fields:
            staff: Staff member taking leave
            start_date: First day of leave period
            end_date: Last day of leave period
            leave_type: Type of leave (annual, sick, or other)
        """
        form = PaidAbsenceForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Form validation failed.")
            return JsonResponse(
                {
                    "success": False,
                    "errors": form.errors,
                    "messages": extract_messages(request),
                },
                status=400,
            )

        staff_member = form.cleaned_data["staff"]
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]
        leave_type = form.cleaned_data["leave_type"]

        if end_date < start_date:
            messages.error(request, "End date must be after start date.")
            return JsonResponse(
                {"success": False, "messages": extract_messages(request)}, status=400
            )

        leave_jobs = {
            "annual": "eecdc751-0207-4f00-a47a-ca025a7cf935",
            "sick": "4dd8ec04-35a0-4c99-915f-813b6b8a3584",
            "other": "cd2085c7-0793-403e-b78d-63b3c134e59d",
        }

        job_pricing = JobPricing.objects.filter(job_id=leave_jobs[leave_type]).first()
        if not job_pricing:
            messages.error(request, "Invalid leave type selected.")
            return JsonResponse(
                {"success": False, "messages": extract_messages(request)}, status=400
            )

        for day in range((end_date - start_date).days + 1):
            date = start_date + timezone.timedelta(days=day)
            if date.weekday() >= 5:  # Skip weekends
                continue

            TimeEntry.objects.create(
                job_pricing=job_pricing,
                staff=staff_member,
                date=date,
                hours=8,
                description=f"{leave_type.capitalize()} Leave",
                is_billable=False,
                note="Automatically created leave entry",
                wage_rate=staff_member.wage_rate,
                charge_out_rate=job_pricing.job.charge_out_rate,
                wage_rate_multiplier=1.0,
            )

        messages.success(request, "Paid absence entries created successfully.")
        return JsonResponse({"success": True, "messages": extract_messages(request)})


class TimesheetDailyView(TemplateView):
    template_name = "time_entries/timesheet_daily_view.html"

    def get(self, request, date=None, *args, **kwargs):
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()

        leave_jobs = {
            "annual": "eecdc751-0207-4f00-a47a-ca025a7cf935",
            "sick": "4dd8ec04-35a0-4c99-915f-813b6b8a3584",
            "other": "cd2085c7-0793-403e-b78d-63b3c134e59d",
        }

        staff_data = []
        total_expected_hours = 0
        total_actual_hours = 0
        total_billable_hours = 0
        total_shop_hours = 0
        total_missing_hours = 0

        for staff_member in filtered_staff:
            scheduled_hours = staff_member.get_scheduled_hours(target_date)
            decimal_scheduled_hours = Decimal(scheduled_hours)

            time_entries = TimeEntry.objects.filter(
                date=target_date, staff=staff_member
            ).select_related("job_pricing")

            paid_leave_entries = time_entries.filter(
                job_pricing__job_id__in=leave_jobs.values()
            )

            has_paid_leave = paid_leave_entries.exists()

            actual_hours = sum(entry.hours for entry in time_entries)

            billable_hours = sum(
                entry.hours for entry in time_entries if entry.is_billable
            )

            shop_hours = sum(
                entry.hours for entry in time_entries if entry.job_pricing.job.shop_job
            )

            missing_hours = (
                decimal_scheduled_hours - actual_hours
                if decimal_scheduled_hours > actual_hours
                else 0
            )

            total_expected_hours += scheduled_hours
            total_actual_hours += actual_hours
            total_billable_hours += billable_hours
            total_shop_hours += shop_hours
            total_missing_hours += missing_hours

            if has_paid_leave:
                status = "Off Today"
                alert = "-"
            elif scheduled_hours == 0:
                status = "Off Today"
                alert = "-"
            elif actual_hours == 0:
                status = "⚠️ Missing"
                alert = f"{decimal_scheduled_hours}hrs needed"
            elif actual_hours < decimal_scheduled_hours and decimal_scheduled_hours > 0:
                status = "⚠️ Missing"
                alert = f"{decimal_scheduled_hours - actual_hours:.1f}hrs needed"
            elif actual_hours > decimal_scheduled_hours:
                status = "⚠️ Overtime"
                alert = f"{actual_hours - decimal_scheduled_hours:.1f}hrs extra"
            else:
                status = "Complete"
                alert = "-"

            staff_data.append(
                {
                    "staff_id": staff_member.id,
                    "name": (staff_member.get_display_full_name()),
                    "last_name": staff_member.last_name,
                    "scheduled_hours": scheduled_hours,
                    "actual_hours": actual_hours,
                    "status": status,
                    "alert": alert,
                    "entries": [
                        {
                            "job_name": entry.job_pricing.job.name,
                            "hours": entry.hours,
                            "is_billable": entry.is_billable,
                        }
                        for entry in time_entries
                    ],
                }
            )

        total_hours = total_actual_hours or 1
        billable_percentage = (total_billable_hours / total_hours) * 100
        shop_percentage = (total_shop_hours / total_hours) * 100

        context = {
            "date": target_date.strftime("%Y-%m-%d"),
            "staff_data": staff_data,
            "daily_summary": {
                "total_expected_hours": total_expected_hours,
                "total_actual_hours": total_actual_hours,
                "total_missing_hours": total_missing_hours,
                "billable_percentage": round(billable_percentage, 1),
                "shop_percentage": round(shop_percentage, 1),
            },
            "context_json": json.dumps(
                {"date": target_date.strftime("%Y-%m-%d"), "staff_data": staff_data},
                cls=DjangoJSONEncoder,
            ),
        }

        return render(request, self.template_name, context)
