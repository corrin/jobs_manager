import base64
import io
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import List

# matplotlib.use('Agg') must be called before importing matplotlib.pyplot
# This configures matplotlib to work without a GUI backend
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views.generic import TemplateView

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff
from apps.job.models import Job, JobPricing
from apps.timesheet.forms import PaidAbsenceForm
from apps.timesheet.models import TimeEntry
from apps.workflow.utils import extract_messages

# Configure logging to only show logs from this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Disable matplotlib debug logging without affecting other loggers
logging.getLogger("matplotlib").propagate = False

# Use the utility function to get excluded staff IDs
EXCLUDED_STAFF_IDS = get_excluded_staff()

# Jobs that won't make part of the graphic
EXCLUDED_JOBS = [
    "Business Development",
    "Bench - busy work",
    "Worker Admin",
    "Office Admin",
    "Annual Leave",
    "Sick Leave",
    "Other Leave",
    "Travel",
    "Training",
]


class TimesheetOverviewView(TemplateView):
    """View for displaying timesheet overview including staff hours, job statistics and graphics."""

    template_name = "timesheet/timesheet_overview.html"

    @classmethod
    def get_filtered_staff(cls) -> List[Staff]:
        """Get filtered staff list excluding certain staff members.

        Returns:
            List[Staff]: Staff objects using model's default ordering (by last_name, first_name),
            excluding staff users and specific IDs.
        """
        return list(
            Staff.objects.exclude(
                models.Q(is_staff=True) | models.Q(id__in=EXCLUDED_STAFF_IDS)
            )
        )

    def get(self, request, start_date=None, *args, **kwargs):
        """Handle GET request to display timesheet overview.

        Args:
            request: The HTTP request
            start_date: Optional start date string in YYYY-MM-DD format

        Returns:
            Rendered template with timesheet data context
        """
        # Check for action in query parameters instead of headers
        action = request.GET.get("action")
        if not action:
            action = request.GET.get("export_to_ims")
        logger.info(f"Logging action {action}")
        start_date = self._get_start_date(start_date)
        match action:
            case "export_to_ims" | "1":
                # Get date from query parameters instead of headers
                query_date = request.GET.get("date")
                return self.export_to_ims(request, self._get_start_date(query_date))
            case _:
                try:
                    week_days = self._get_week_days(start_date)
                    prev_week_url, next_week_url = self._get_navigation_urls(start_date)
                    staff_data, totals = self._get_staff_data(week_days)
                    graphic_html = self._generate_graphic()

                    context = {
                        "week_days": week_days,
                        "staff_data": staff_data,
                        "weekly_summary": self._format_weekly_summary(totals),
                        "job_count": self._get_open_jobs().count(),
                        "graphic": graphic_html,
                        "prev_week_url": prev_week_url,
                        "next_week_url": next_week_url,
                    }

                    return render(request, self.template_name, context)
                except Exception as e:
                    logger.error(f"Error in TimesheetOverviewView.get: {str(e)}")
                    messages.error(
                        request,
                        "An error occurred while loading the timesheet overview.",
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
            ).exclude(name__in=EXCLUDED_JOBS)
        except Exception as e:
            logger.error(f"Error getting open jobs: {str(e)}")
            return Job.objects.none()

    def _get_start_date(self, start_date):
        """Parse and validate the start date.

        Args:
            start_date: Date string in YYYY-MM-DD format

        Returns:
            datetime.date object for start date, defaulting to Monday of current week
        """
        if start_date:
            try:
                return datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError as e:
                logger.warning(f"Invalid start date format: {str(e)}")
                # Get Monday of current week
                today = timezone.now().date()
                return today - timezone.timedelta(days=today.weekday())
        # Get Monday of current week if no start_date provided
        today = timezone.now().date()
        return today - timezone.timedelta(days=today.weekday())

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

    def _get_ims_week(self, start_date):
        """Returns a list of IMS week days (Tuesday, Wednesday, Thursday, Friday and next Monday),
        adjusting the date to Tuesday and skipping weekends.

        Args:
            start_date: datetime.date – reference date

        Returns:
            List of datetime.date with IMS week days.
        """
        logger.info(f"[_get_ims_week] Start date received: {start_date}")
        try:
            # Determine the corresponding Tuesday:
            # If it's Monday (weekday == 0), Tuesday was 6 days ago;
            # Otherwise, subtract (weekday - 1) days.
            # E.g.: it's thursday (3). We get 3 - 1 = 2, and then subtract 2 days from thursday, which led us to Tuesday
            if start_date.weekday() == 0:
                tuesday = start_date - timezone.timedelta(days=6)
            else:
                tuesday = start_date - timezone.timedelta(
                    days=(start_date.weekday() - 1)
                )

            # Build the IMS week:
            # Tuesday, Wednesday, Thursday, Friday and next Monday (6 days after Tuesday)
            ims_week = [
                tuesday,  # Tuesday
                tuesday + timezone.timedelta(days=1),  # Wednesday
                tuesday + timezone.timedelta(days=2),  # Thursday
                tuesday + timezone.timedelta(days=3),  # Friday
                tuesday + timezone.timedelta(days=6),  # Next Monday
            ]
            return ims_week
        except Exception as e:
            logger.error(f"Error getting IMS week: {str(e)}")
            return None

    def _get_navigation_urls(self, start_date):
        """Get URLs for previous and next week navigation.

        Args:
            start_date: datetime.date object for current week

        Returns:
            Tuple of (prev_week_url, next_week_url)
        """
        prev_week_date = start_date - timezone.timedelta(days=7)
        next_week_date = start_date + timezone.timedelta(days=7)

        prev_week_url = reverse(
            "timesheet:timesheet_overview_with_date",
            kwargs={"start_date": prev_week_date.strftime("%Y-%m-%d")},
        )
        next_week_url = reverse(
            "timesheet:timesheet_overview_with_date",
            kwargs={"start_date": next_week_date.strftime("%Y-%m-%d")},
        )

        return prev_week_url, next_week_url

    def _get_staff_data(self, week_days, export_to_ims=False):
        staff_data = []
        total_hours = 0
        total_billable_hours = 0

        for staff_member in self.get_filtered_staff():
            weekly_hours = []
            total_staff_std_hours = 0
            total_staff_ovt_hours = 0
            billable_hours = 0

            total_staff_standard_hours = 0
            total_staff_time_and_half_hours = 0
            total_staff_double_time_hours = 0
            total_staff_annual_leave_hours = 0
            total_staff_sick_leave_hours = 0
            total_staff_other_leave_hours = 0

            for day in week_days:
                if export_to_ims:
                    daily_data = self._get_ims_data(staff_member, day)
                else:
                    daily_data = self._get_daily_data(staff_member, day)

                weekly_hours.append(daily_data["daily_summary"])
                total_staff_std_hours += daily_data["hours"]

                if export_to_ims:
                    # Add overtime hours
                    total_staff_ovt_hours += daily_data["overtime"]

                    # Aggregate hours by type
                    total_staff_standard_hours += daily_data["daily_summary"].get(
                        "standard_hours", 0
                    )
                    total_staff_time_and_half_hours += daily_data["daily_summary"].get(
                        "time_and_half_hours", 0
                    )
                    total_staff_double_time_hours += daily_data["daily_summary"].get(
                        "double_time_hours", 0
                    )

                    # Check for leave type and add to appropriate total
                    if daily_data["daily_summary"].get("status") == "Leave":
                        leave_type = (
                            daily_data["daily_summary"].get("leave_type", "").lower()
                        )
                        leave_hours = daily_data["leave_hours"]

                        if "annual" in leave_type:
                            total_staff_annual_leave_hours += leave_hours
                        if "sick" in leave_type:
                            total_staff_sick_leave_hours += leave_hours
                        if "other" in leave_type:
                            total_staff_other_leave_hours += leave_hours

                billable_hours += daily_data.get("billable_hours", 0)

            total_leave_hours = (
                total_staff_annual_leave_hours
                + total_staff_sick_leave_hours
                + total_staff_other_leave_hours
            )

            staff_entry = {
                "staff_id": staff_member.id,
                "name": staff_member.get_display_full_name(),
                "weekly_hours": weekly_hours,
                "total_hours": total_staff_std_hours,
                "total_overtime": total_staff_ovt_hours,
                "billable_percentage": self._calculate_percentage(
                    billable_hours, total_staff_std_hours
                ),
                "total_billable_hours": billable_hours,
            }

            if export_to_ims:
                staff_entry.update(
                    {
                        "total_standard_hours": total_staff_standard_hours,
                        "total_time_and_half_hours": total_staff_time_and_half_hours,
                        "total_double_time_hours": total_staff_double_time_hours,
                        "total_annual_leave_hours": total_staff_annual_leave_hours,
                        "total_sick_leave_hours": total_staff_sick_leave_hours,
                        "total_other_leave_hours": total_staff_other_leave_hours,
                        "total_leave_hours": total_leave_hours,
                    }
                )

            staff_data.append(staff_entry)

            total_hours += total_staff_std_hours + total_staff_ovt_hours
            total_billable_hours += billable_hours

        totals = {
            "total_hours": total_hours,
            "billable_percentage": self._calculate_percentage(
                total_billable_hours, total_hours
            ),
        }
        return staff_data, totals

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

    def _get_ims_data(self, staff_member, day):
        try:
            scheduled_hours = staff_member.get_scheduled_hours(day)
            time_entries = TimeEntry.objects.filter(
                staff=staff_member, date=day
            ).select_related("job_pricing")

            daily_hours = sum(entry.hours for entry in time_entries)
            daily_billable_hours = sum(
                entry.hours for entry in time_entries if entry.is_billable
            )

            leave_entries = time_entries.filter(
                job_pricing__job__name__icontains="Leave"
            )
            has_paid_leave = leave_entries.exists()
            leave_type = None
            leave_hours = Decimal(0)

            if has_paid_leave:
                if leave_entries.count() > 1:
                    logger.warning(
                        f"Multiple leave entries found for {staff_member} on {day}"
                    )
                    leave_type = leave_entries.first().job_pricing.job.name
                else:
                    leave_type = leave_entries.first().job_pricing.job.name

                leave_hours = sum(entry.hours for entry in leave_entries)

            non_leave_entries = time_entries.exclude(
                job_pricing__job__name__icontains="Leave"
            )

            # Convert scheduled_hours to Decimal before calculation
            overtime = (
                Decimal(daily_hours) - Decimal(scheduled_hours)
                if daily_hours > scheduled_hours
                else 0
            )

            # Accumulate hours by rate type ONLY for non-leave entries
            standard_hours = Decimal(0)
            time_and_half_hours = Decimal(0)
            double_time_hours = Decimal(0)
            unpaid_hours = Decimal(0)
            for entry in non_leave_entries:
                multiplier = Decimal(entry.wage_rate_multiplier)
                match multiplier:
                    case 1.0:
                        standard_hours += entry.hours
                    case 1.5:
                        time_and_half_hours += entry.hours
                    case 2.0:
                        double_time_hours += entry.hours
                    case 0.0:
                        unpaid_hours += entry.hours

            return {
                "hours": daily_hours,
                "billable_hours": daily_billable_hours,
                "overtime": overtime,
                "leave_hours": leave_hours,
                "daily_summary": {
                    "day": day,
                    "hours": daily_hours,
                    "status": self._get_status(
                        daily_hours, scheduled_hours, has_paid_leave
                    ),
                    "leave_type": leave_type if leave_type else None,
                    "standard_hours": standard_hours,
                    "time_and_half_hours": time_and_half_hours,
                    "double_time_hours": double_time_hours,
                    "unpaid_hours": unpaid_hours,
                    "overtime": overtime,
                    "leave_hours": leave_hours,
                },
            }
        except Exception as e:
            logger.error(
                f"Error getting IMS data for {staff_member} on {day}: {str(e)}"
            )
            return {
                "hours": 0,
                "billable_hours": 0,
                "overtime": 0,
                "leave_hours": 0,
                "daily_summary": {
                    "day": day,
                    "hours": 0,
                    "status": "⚠",
                    "standard_hours": 0,
                    "time_and_half_hours": 0,
                    "double_time_hours": 0,
                    "leave_hours": 0,
                    "unpaid_hours": 0,
                },
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
        match action:
            case "load_paid_absence_form":
                return self.load_paid_absence_form(request)
            case "submit_paid_absence":
                return self.submit_paid_absence(request)
            case _:
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
            "timesheet/paid_absence_form.html",
            {"form": form, "staff_members": self.get_filtered_staff()},
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

        # Get leave job IDs dynamically instead of hardcoding them
        leave_jobs = {}
        leave_types = {
            "annual": "Annual Leave",
            "sick": "Sick Leave",
            "other": "Other Leave",
        }

        for leave_key, leave_name in leave_types.items():
            job = Job.objects.filter(name=leave_name).first()
            if job:
                leave_jobs[leave_key] = str(job.id)
            else:
                logger.error(f"Leave job '{leave_name}' not found in database")
                messages.error(
                    request, f"Leave type '{leave_name}' not configured in system."
                )
                return JsonResponse(
                    {"success": False, "messages": extract_messages(request)},
                    status=400,
                )

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

    def export_to_ims(self, request, start_date):
        try:
            week_days = self._get_ims_week(start_date)
            prev_week_url, next_week_url = self._get_navigation_urls(start_date)
            staff_data, totals = self._get_staff_data(week_days, export_to_ims=True)

            return JsonResponse(
                {
                    "success": True,
                    "staff_data": staff_data,
                    "totals": totals,
                    "prev_week_url": prev_week_url,
                    "next_week_url": next_week_url,
                    "week_days": week_days,
                },
                status=200,
            )
        except Exception as e:
            logger.error(f"Error exporting to IMS: {str(e)}")
            messages.error(request, "Error exporting to IMS")
            return JsonResponse(
                {
                    "error": "Error exporting to IMS",
                    "messages": extract_messages(request),
                },
                status=500,
            )


class TimesheetDailyView(TemplateView):
    template_name = "timesheet/timesheet_daily_view.html"

    @classmethod
    def get_filtered_staff(cls) -> List[Staff]:
        """Get filtered staff list excluding certain staff members.

        Returns:
            List[Staff]: Staff objects using model's default ordering (by last_name, first_name),
            excluding staff users and specific IDs.
        """
        return list(
            Staff.objects.exclude(
                models.Q(is_staff=True) | models.Q(id__in=EXCLUDED_STAFF_IDS)
            )
        )

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

        for staff_member in self.get_filtered_staff():
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
            "date": target_date.strftime(
                "%Y-%m-%d"
            ),  # Keep original format for HTML date input
            "date_nz": target_date.strftime("%d/%m/%Y"),  # Add NZ formatted date
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
