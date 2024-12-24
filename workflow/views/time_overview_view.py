import json
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import TemplateView

from workflow.models import Job, Staff, TimeEntry


class TimesheetOverviewView(TemplateView):
    template_name = "time_entries/timesheet_overview.html"

    def get(self, request, start_date=None, *args, **kwargs):
        # Step 1: Determine the start date
        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                # If the date format is incorrect, default to today minus 7 days
                start_date = timezone.now().date() - timezone.timedelta(days=7)
        else:
            # Default to showing the last 7 days ending yesterday
            start_date = timezone.now().date() - timezone.timedelta(days=7)

        # Step 2: Calculate the last 7 days starting from the start date
        last_seven_days = [start_date - timezone.timedelta(days=i) for i in range(7)]

        # Step 3: Get all staff members and their hours by day
        staff_data = []
        all_staff = Staff.objects.all()
        for staff_member in all_staff:
            # App users (Django admins, etc.) are not workers in the factory and so should not be having timesheet entries
            if staff_member.is_staff is True:
                continue
            staff_hours = []
            for day in last_seven_days:
                scheduled_hours = staff_member.get_scheduled_hours(
                    day
                )  # Hours they're rostered to work
                staff_hours.append(
                    {
                        "date": day.strftime("%Y-%m-%d"),
                        "scheduled_hours": scheduled_hours,
                    }
                )
            staff_data.append(
                {
                    "staff_id": staff_member.id,
                    "staff_name": staff_member.get_display_name(),
                    "hours_by_day": staff_hours,
                }
            )

        # Step 4: Get all open jobs and their hours
        job_data = []
        open_jobs = Job.objects.filter(
            status__in=["quoting", "approved", "in_progress", "special"]
        )

        for job in open_jobs:
            # Get estimated hours, quoted hours, and actual hours
            reality = job.latest_reality_pricing
            estimated_hours = job.latest_estimate_pricing.total_hours
            quoted_hours = job.latest_quote_pricing.total_hours
            actual_entries = job.latest_reality_pricing.time_entries.all()
            actual_total_hours = sum(entry.hours for entry in actual_entries)
            actual_billable_hours = sum(
                entry.hours for entry in actual_entries if entry.is_billable
            )
            job_data.append(
                {
                    "job_id": job.id,
                    "job_name": job.name,
                    "estimated_hours": estimated_hours,
                    "quoted_hours": quoted_hours,
                    "actual_hours_to_date": actual_total_hours,
                    "actual_billable_hours_to_date": actual_billable_hours,
                    "actual_time_revenue_to_date": reality.total_time_revenue,
                    "actual_time_cost_to_date": reality.total_time_cost,
                    "actual_total_revenue_to_date": reality.total_revenue,
                    "actual_total_cost_to_date": reality.total_cost,
                    "shop_job": job.shop_job,
                }
            )

        # Step 5: Get all timesheets in that week
        timesheet_entries = []
        time_entries = TimeEntry.objects.filter(
            date__in=last_seven_days
        ).select_related("staff", "job_pricing")
        for entry in time_entries:
            timesheet_entries.append(
                {
                    "date": entry.date.strftime("%Y-%m-%d"),
                    "staff_member": (
                        entry.staff.get_display_name() if entry.staff else "Unknown"
                    ),
                    "job_name": entry.job_pricing.job.name,
                    "hours_worked": entry.hours,
                    "is_billable": entry.is_billable,
                    "wage_rate": entry.wage_rate,
                    "charge_out_rate": entry.charge_out_rate,
                }
            )

        # Prepare context for rendering
        context = {
            "start_date": start_date,
            "staff_data": staff_data,
            "job_data": job_data,
            "timesheet_entries": timesheet_entries,
            "last_seven_days": last_seven_days,
            "context_json": json.dumps(
                {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "staff_data": staff_data,
                    "job_data": job_data,
                    "timesheet_entries": timesheet_entries,
                    "last_seven_days": [
                        day.strftime("%Y-%m-%d") for day in last_seven_days
                    ],
                },
                indent=2,
                cls=DjangoJSONEncoder,
            ),  # Pretty-print for readability
        }

        return render(request, self.template_name, context)


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

        staff_data = []
        for staff_member in Staff.objects.all():
            # See TimesheetOverviewView, lines under "all_staff = ..." 
            if staff_member.is_staff is True:
                continue
            scheduled_hours = staff_member.get_scheduled_hours(target_date)
            time_entries = TimeEntry.objects.filter(
                date=target_date, staff=staff_member
            ).select_related("job_pricing")

            actual_hours = sum(entry.hours for entry in time_entries)

            staff_data.append(
                {
                    "staff_id": staff_member.id,
                    "name": staff_member.preferred_name if staff_member.preferred_name else staff_member.get_display_name(),
                    "last_name": staff_member.last_name,
                    "scheduled_hours": scheduled_hours,
                    "actual_hours": actual_hours,
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

        context = {
            "date": target_date.strftime("%Y-%m-%d"),
            "staff_data": staff_data,
            "context_json": json.dumps(
                {"date": target_date.strftime("%Y-%m-%d"), "staff_data": staff_data},
                cls=DjangoJSONEncoder,
            ),
        }

        return render(request, self.template_name, context)
        # Step 2: Retrieve all time entries for the given date
        time_entries = TimeEntry.objects.filter(date=target_date).select_related(
            "staff", "job_pricing"
        )
        data = []

        for entry in time_entries:
            # Use reality_pricing for actual work done during time entry
            reality_pricing = entry.job_pricing.reality_pricing

            data.append(
                {
                    "staff_member": entry.staff.get_display_name(),
                    "date": entry.date.strftime("%Y-%m-%d"),
                    "job_name": reality_pricing.job.name,
                    "hours_worked": entry.hours_worked,
                    "billable": entry.billable,
                    "job_type": reality_pricing.job.type,
                    "estimated_hours": self.get_estimated_hours(reality_pricing.job),
                    "is_closed": reality_pricing.job.is_closed,
                }
            )

            # Step 3: Check if it is an AJAX request
            if request.headers.get(
                "x-requested-with"
            ) == "XMLHttpRequest" or request.GET.get("ajax"):
                # Return the raw data as JSON
                return JsonResponse(data, safe=False)

        # Step 4: Normal request, render the HTML template
        context = {"date": target_date.strftime("%Y-%m-%d")}
        return render(request, self.template_name, context)
