import decimal
import json
import logging
import math
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import CharField, Func, IntegerField, Value
from django.db.models.functions import Coalesce, Concat
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.accounts.models import Staff
from apps.accounts.utils import get_excluded_staff
from apps.job.models import Job
from apps.job.utils import get_active_jobs, get_jobs_data
from apps.timesheet.enums import RateType
from apps.timesheet.models import TimeEntry
from apps.timesheet.serializers import (
    TimeEntryForTimeEntryViewSerializer as TimeEntrySerializer,
)
from apps.workflow.utils import extract_messages

logger = logging.getLogger(__name__)


def sanitize_decimal_input(raw_value, default=Decimal(0)):
    """
    Sanitizes a raw input value to ensure it's a valid Decimal.
    Handles None, NaN, Infinity, and conversion errors.
    """
    if raw_value is None:
        logger.warning(f"Sanitizing None to {default}.")
        return default
    if isinstance(raw_value, float) and (
        math.isnan(raw_value) or math.isinf(raw_value)
    ):
        logger.warning(f"Sanitizing invalid float {raw_value} to {default}.")
        return default
    try:
        # Convert to string first to handle floats safely
        # and allow Decimal to parse strings.
        val_str = str(raw_value)
        d = decimal.Decimal(val_str)  # Use decimal.Decimal to avoid conflict
        if d.is_nan() or d.is_infinite():
            logger.warning(f"Sanitizing Decimal special value {d} to {default}.")
            return default
        return d
    except (decimal.InvalidOperation, TypeError, ValueError) as e:
        logger.warning(
            (
                f"Sanitizing invalid decimal input '{raw_value}' "
                f"(type: {type(raw_value)}) to {default} due to {e}."
            )
        )
        return default


class TimesheetEntryView(TemplateView):
    """
    View to manage and display timesheet entries for a specific staff member and date.

    Purpose:
    - Centralizes the logic for rendering the timesheet entry page.
    - Dynamically loads staff, jobs, and timesheet data based on the provided
      date and staff ID.
    - Ensures access control and context consistency for the user interface.

    Key Features:
    - Excludes specific staff members (e.g., app/system users) from being displayed.
    - Prepares the context with data necessary for rendering the timesheet
      entry page.
    - Supports navigation between staff members for the same timesheet date.

    Attributes:
    - `template_name` (str): Path to the template used for rendering the view.
    - `EXCLUDED_STAFF_IDS` (list): List of Django staff IDs to be excluded
      from timesheet views.

    Usage:
    - Accessed via a URL pattern that includes the date and staff ID as parameters.
    - Provides the back-end logic for the
      `time_entries/timesheet_entry.html` template.
    """

    template_name = "timesheet/timesheet_entry.html"

    # Excluding app users ID's to avoid them being loaded in timesheet views
    # because they do not have entries
    # (Valerie and Corrin included as they are not supposed to enter hours)
    EXCLUDED_STAFF_IDS = get_excluded_staff()

    def get(self, request, date, staff_id, *args, **kwargs):
        """
        Handles GET requests to display the timesheet entry page for a given
        staff member and date.

        Purpose:
        - Retrieves and validates the date and staff member based on
          URL parameters.
        - Fetches timesheet entries, open jobs, and navigation details
          for the UI.
        - Ensures the context contains all data needed to render the page.

        Workflow:
        1. Validates the `date` parameter to ensure it is in the correct
           format (YYYY-MM-DD).
        2. Checks if the `staff_id` is excluded. If so, denies access.
        3. Retrieves the staff member and raises a 404 error if not found.
        4. Queries:
            - Timesheet entries for the specified date and staff member.
            - Open jobs for potential assignment.
        5. Prepares navigation details for moving between staff members.
        6. Constructs the context for rendering the page.

        Parameters:
        - `request`: The HTTP GET request.
        - `date` (str): The target date for the timesheet.
        - `staff_id` (UUID): The ID of the staff member.

        Returns:
        - Rendered HTML template with the context for the timesheet
          entry page.

        Error Handling:
        - Raises `ValueError` for invalid date formats.
        - Raises `PermissionError` if the staff member is excluded.
        - Raises `Http404` if the staff member is not found.

        Context:
        - Includes data for the staff member, timesheet entries, open jobs,
          and navigation links.

        Dependencies:
        - `Staff`, `TimeEntry`, and `Job` models for querying database records.
        - `json.dumps` for serializing data to JSON format.
        - `DjangoJSONEncoder` for handling complex data types.
        - Template: `time_entries/timesheet_entry.html`.

        Notes:
        - The `EXCLUDED_STAFF_IDS` attribute should be updated as needed to
          reflect changes in app/system users.
        """
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

        if staff_id in self.EXCLUDED_STAFF_IDS:
            raise PermissionError("Access denied for this staff member")

        try:
            staff_member = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise Http404("Staff member not found")

        all_staff = self._get_staff_navigation_list(self.EXCLUDED_STAFF_IDS)

        # Locate the index of the current staff.
        staff_index = next(
            (index for index, s in enumerate(all_staff) if s["id"] == staff_id), None
        )
        if staff_index is None:
            raise Http404("Staff member not found in ordered list")

        # Compute circular navigation indexes.
        next_index = (staff_index + 1) % len(all_staff)
        prev_index = (staff_index - 1) % len(all_staff)

        next_staff = {
            "id": all_staff[next_index]["id"],
            "name": all_staff[next_index]["display_full_name"],
        }
        prev_staff = {
            "id": all_staff[prev_index]["id"],
            "name": all_staff[prev_index]["display_full_name"],
        }

        time_entries = (
            TimeEntry.objects.filter(date=target_date, staff_id=staff_id)
            .select_related("job_pricing__latest_reality_for_job__client")
            .values(
                "id",
                "job_pricing_id",
                "job_pricing__job__job_number",
                "job_pricing__job__name",
                "job_pricing__job__client__name",
                "description",
                "hours",
                "wage_rate_multiplier",
                "is_billable",
                "note",
            )
        )

        timesheet_data = [
            {
                "id": str(entry["id"]),
                "job_pricing_id": entry["job_pricing_id"],
                "job_number": entry["job_pricing__job__job_number"],
                "job_name": entry["job_pricing__job__name"],
                "client_name": (
                    entry["job_pricing__job__client__name"] or "No client!?"
                ),
                "description": entry["description"] or "",
                "hours": float(entry["hours"]),
                "rate_multiplier": float(entry["wage_rate_multiplier"]),
                "is_billable": entry["is_billable"],
                "notes": entry["note"] or "",
                "timesheet_date": target_date.strftime("%Y-%m-%d"),
            }
            for entry in time_entries
        ]

        # Use the refactored utility function to get active jobs
        open_jobs = get_active_jobs()  # Already includes select_related('client')
        # Add other select_related if needed specifically here
        open_jobs = open_jobs.select_related(
            "latest_estimate_pricing", "latest_reality_pricing"
        )

        jobs_data = [
            {
                "id": str(job.id),
                "job_number": job.job_number,
                "name": job.name,
                "job_display_name": f"{job.job_number} - {job.name}",
                "estimated_hours": (
                    job.latest_estimate_pricing.total_hours
                    if job.latest_estimate_pricing
                    else 0
                ),
                "hours_spent": (
                    job.latest_reality_pricing.total_hours
                    if job.latest_reality_pricing
                    else 0
                ),
                "client_name": (job.client.name if job.client else "NO CLIENT!?"),
                "charge_out_rate": float(job.charge_out_rate),
                "job_status": job.status,
            }
            for job in open_jobs
        ]

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"time_entries": timesheet_data, "jobs": jobs_data})

        context = {
            "staff_member": staff_member,
            "staff_member_json": json.dumps(
                {
                    "id": staff_member.id,
                    "name": f"{staff_member.first_name} {staff_member.last_name}",
                    "wage_rate": staff_member.wage_rate,
                    "scheduled_hours": float(
                        staff_member.get_scheduled_hours(target_date)
                    ),
                },
                cls=DjangoJSONEncoder,
            ),
            "timesheet_date": target_date.strftime("%Y-%m-%d"),
            "timesheet_entries_json": json.dumps(timesheet_data, cls=DjangoJSONEncoder),
            "jobs_json": json.dumps(jobs_data, cls=DjangoJSONEncoder),
            "next_staff": next_staff,
            "prev_staff": prev_staff,
        }

        return render(request, self.template_name, context)

    def _get_staff_navigation_list(self, excluded_ids, cache_timeout=3600):
        """
        Retrieves the ordered staff list for navigation, annotated with a
        computed display_full_name.

        Intention:
        - Compute the display_first_name using only the first token of the
          preferred_name (or first_name).
        - Concatenate it with the full last_name to get
          display_full_name.
        - Order by display_full_name.
        - Cache the resulting list to reduce database load if the staff
          list does not change frequently.

        Parameters:
        - excluded_ids: List or set of staff IDs to exclude.
        - cache_timeout (int): The time in seconds for which the result
          should be cached.

        Returns:
        - A list of dictionaries with keys 'id' and 'display_full_name'.
        """
        cache_key = "staff_navigation_list"
        staff_list = cache.get(cache_key)
        if staff_list is None:
            staff_queryset = (
                Staff.objects.exclude(id__in=excluded_ids)
                .annotate(
                    display_first_name=Func(
                        Coalesce("preferred_name", "first_name"),
                        Value(" "),
                        Value(1, output_field=IntegerField()),
                        function="substring_index",
                        output_field=CharField(),
                    ),
                    display_full_name=Concat(
                        "display_first_name",
                        Value(" "),
                        "last_name",
                        output_field=CharField(),
                    ),
                )
                .order_by("last_name", "display_first_name")
            )
            staff_list = list(staff_queryset.values("id", "display_full_name"))
            cache.set(cache_key, staff_list, timeout=cache_timeout)
        return staff_list


@require_http_methods(["POST"])
def autosave_timesheet_view(request):
    """
    Handles autosave requests for timesheet data.

    Purpose:
    - Automates the saving of timesheet changes, including updates,
      creations, and deletions.
    - Dynamically updates related jobs and entries in the front-end.
    - Ensures data consistency and prevents duplication during
      processing.

    Workflow:
    1. Parsing and Validation:
    - Parses the incoming request body as JSON.
    - Separates entries into `time_entries` (to save or update) and
      `deleted_entries` (to remove).

    2. Deletion Processing:
    - Deletes specified entries by ID if they exist.
    - Removes related jobs from the current job list.
    - Logs any missing entries without causing failures.

    3. Time Entry Processing:
    - Skips incomplete or invalid entries.
    - Updates existing entries or creates new ones while avoiding
      duplicates.
    - Adds or updates jobs related to new or updated entries.

    4. Response:
    - Returns success responses with related jobs, action type
      (`add` or `remove`), and feedback messages.
    - Sends error responses for invalid data or unexpected issues.

    Parameters:
    - `request` (HttpRequest): The HTTP POST request containing timesheet
      data in JSON format.

    Error Handling:
    - Validates JSON format and structure (`time_entries` and `deleted_entries`).
    - Catches invalid data or missing fields gracefully, skipping problematic entries.
    - Logs unexpected exceptions and provides feedback for debugging.

    Dependencies:
    - Django Models (`TimeEntry`, `Job`, `Staff`) for database operations.
    - Utility Functions:
    - `extract_messages`: Extracts feedback messages for the front-end.
    - `get_jobs_data`: Retrieves data for jobs related to the processed entries.
    - `RateType`: Manages wage rate multipliers for time entries.

    Usage:
    - Triggered via AJAX POST requests from the front-end grid.
    - Supports real-time autosaving and deletion of entries with minimal latency.

    Notes:
    - Designed for efficient bulk processing to reduce server load.
    - Ensures traceability with extensive logging.
    - Prevents duplicate entries by verifying existing records with matching attributes.
    """
    try:
        logger.debug("Timesheet autosave request received")
        data = json.loads(request.body)
        logger.info("Request data: %s", json.dumps(data, indent=2))
        time_entries = data.get("time_entries", [])
        deleted_entries = data.get("deleted_entries", [])

        related_jobs = set()

        logger.debug(f"Number of time entries: {len(time_entries)}")
        logger.debug(f"Number of entries to delete: {len(deleted_entries)}")

        if deleted_entries:
            for entry_id in deleted_entries:
                logger.debug(f"Deleting entry with ID: {entry_id}")

                try:
                    entry = TimeEntry.objects.get(id=entry_id)
                    related_jobs.add(entry.job_pricing.job_id)
                    messages.success(request, "Timesheet deleted successfully")
                    entry.delete()
                    logger.debug(f"Entry with ID {entry_id} deleted successfully")

                except TimeEntry.DoesNotExist:
                    logger.error(f"TimeEntry with ID {entry_id} not found for deletion")
            return JsonResponse(
                {
                    "success": True,
                    "jobs": get_jobs_data(related_jobs),
                    "action": "remove",
                    "messages": extract_messages(request),
                },
                status=200,
            )

        if not time_entries and not deleted_entries:
            logger.error("No valid entries to process")
            messages.info(request, "No changes to save.")
            return JsonResponse(
                {
                    "error": "No time entries provided",
                    "messages": extract_messages(request),
                },
                status=400,
            )

        updated_entries = []
        for entry_data in time_entries:
            if not entry_data.get("job_number") or not entry_data.get("hours"):
                logger.debug("Skipping incomplete entry: ", entry_data)
                continue

            entry_id = entry_data.get("id")
            logger.debug(f"Entry: {json.dumps(entry_data, indent=2)}")
            job_data = entry_data.get("job_data")
            logger.debug(f"Job data: {json.dumps(job_data, indent=2)}")
            job_id = job_data.get("id") if job_data else None
            logger.debug(f"Job ID: {job_id}")

            if not job_id:
                logger.error("Missing job ID in entry data")
                continue

            hours_raw = entry_data.get("hours", 0)
            hours = sanitize_decimal_input(hours_raw)

            try:
                timesheet_date = entry_data.get("timesheet_date", None)
                if not timesheet_date:
                    logger.error("Missing timesheet_date in entry data")
                    continue

                target_date = datetime.strptime(timesheet_date, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                logger.error(
                    f"Invalid timesheet_date format: {entry_data.get('timesheet_date')}"
                )
                continue

            description = entry_data.get("description", "").strip()

            if entry_id and entry_id != "tempId":
                try:
                    logger.debug(f"Processing entry with ID: {entry_id}")
                    entry = TimeEntry.objects.get(id=entry_id)

                    if entry.staff is None:
                        logger.warning(f"Entry {entry_id} has no staff assigned")
                        staff_id = entry_data.get("staff_id")
                        if staff_id:
                            try:
                                staff = Staff.objects.get(id=staff_id)
                                entry.staff = staff
                                logger.info(
                                    (
                                        f"Restored staff {staff.name} assignment "
                                        f"for entry {entry.id}"
                                    )
                                )
                            except Staff.DoesNotExist:
                                logger.error(f"Staff with ID {staff_id} not found")
                        else:
                            logger.error(f"Staff ID not provided for entry {entry.id}")
                            raise ValueError("Staff ID not provided")
                    # Identify old job before changing
                    old_job_id = (
                        entry.job_pricing.job.id if entry.job_pricing.job else None
                    )
                    old_job = Job.objects.get(id=old_job_id) if old_job_id else None

                    if job_id != str(entry.job_pricing.job.id):
                        logger.info(f"Job for entry {entry_id} changed to {job_id}")
                        new_job = Job.objects.get(id=job_id)
                        entry.job_pricing = new_job.latest_reality_pricing

                    # Update existing entry
                    entry.description = description
                    entry.hours = hours
                    entry.is_billable = entry_data.get("is_billable", True)
                    entry.items = entry_data.get("items", entry.items)

                    minutes_per_item_raw = entry_data.get(
                        "mins_per_item", entry.minutes_per_item
                    )
                    entry.minutes_per_item = sanitize_decimal_input(
                        minutes_per_item_raw
                    )

                    entry.note = entry_data.get("notes", "")
                    entry.wage_rate_multiplier = RateType(
                        entry_data.get("rate_type", "Ord")
                    ).multiplier

                    charge_out_rate_raw = job_data.get(
                        "charge_out_rate", entry.charge_out_rate
                    )
                    entry.charge_out_rate = sanitize_decimal_input(charge_out_rate_raw)

                    related_jobs.add(job_id)
                    entry.save()
                    updated_entries.append(entry)
                    job = entry.job_pricing.job

                    scheduled_hours = entry.staff.get_scheduled_hours(target_date)
                    if scheduled_hours < hours:
                        messages.warning(
                            request,
                            (
                                f"Existing timesheet saved successfully, but hours "
                                f"exceed scheduled hours for {target_date}"
                            ),
                        )
                    elif job.status in ["completed", "quoting"]:
                        messages.error(
                            request,
                            f"Timesheet saved, but note job status is {job.status}.",
                        )
                    else:
                        messages.success(
                            request, "Existing timesheet saved successfully"
                        )
                    logger.debug("Existing timesheet saved successfully")

                    return JsonResponse(
                        {
                            "success": True,
                            "entry": TimeEntrySerializer(entry).data,
                            "jobs": get_jobs_data(related_jobs),
                            "remove_jobs": (
                                [get_jobs_data([str(old_job.id)])] if old_job else []
                            ),
                            "action": "update",
                            "messages": extract_messages(request),
                        },
                        status=200,
                    )

                except TimeEntry.DoesNotExist:
                    logger.error(f"TimeEntry with ID {entry_id} not found")

            else:
                # Verify if there's already a registry with same data to avoid
                # creating multiple entries
                job = Job.objects.get(id=job_id)
                job_pricing = job.latest_reality_pricing
                staff = Staff.objects.get(id=entry_data.get("staff_id"))

                existing_entry = TimeEntry.objects.filter(
                    job_pricing__job_id=job_id,
                    staff_id=entry_data.get("staff_id"),
                    date=target_date,
                    description=description,
                    hours=hours,
                ).first()

                if existing_entry:
                    logger.info(f"Found duplicated entry: {existing_entry.id}")
                    continue

                date_str = entry_data.get("timesheet_date")
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                minutes_per_item_val = sanitize_decimal_input(
                    entry_data.get("mins_per_item", 0)
                )
                charge_out_rate_val = sanitize_decimal_input(
                    job_data.get("charge_out_rate", 0)
                )

                entry = TimeEntry.objects.create(
                    job_pricing=job_pricing,
                    staff=staff,
                    date=target_date,
                    description=description,
                    hours=hours,
                    items=entry_data.get("items"),
                    minutes_per_item=minutes_per_item_val,
                    is_billable=entry_data.get("is_billable", True),
                    note=entry_data.get("notes", ""),
                    wage_rate_multiplier=RateType(entry_data["rate_type"]).multiplier,
                    wage_rate=staff.wage_rate,
                    charge_out_rate=charge_out_rate_val,
                )

                updated_entries.append(entry)
                related_jobs.add(job_id)

                scheduled_hours = entry.staff.get_scheduled_hours(target_date)
                if scheduled_hours < hours:
                    warning_msg = (
                        "Timesheet created successfully, but hours exceed "
                        f"scheduled hours for {target_date}"
                    )
                    messages.warning(request, warning_msg)
                elif job.status in ["completed", "quoting"]:
                    error_msg = (
                        f"Timesheet created successfully, but note job status is "
                        f"{job.status}."
                    )
                    messages.error(request, error_msg)
                else:
                    messages.success(request, "Timesheet created successfully.")
                logger.debug("Timesheet created successfully")

                return JsonResponse(
                    {
                        "success": True,
                        "messages": extract_messages(request),
                        "entry": TimeEntrySerializer(entry).data,
                        "jobs": get_jobs_data(related_jobs),
                        "action": "add",
                    },
                    status=200,
                )

        return JsonResponse(
            {
                "success": True,
                "messages": extract_messages(request),
                "entries": TimeEntrySerializer(updated_entries, many=True).data,
                "jobs": get_jobs_data(related_jobs),
                "remove_jobs": [get_jobs_data([str(old_job.id)])] if old_job else [],
                "action": "update",
            }
        )

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        messages.error(request, "Failed to parse JSON")
        return JsonResponse(
            {"error": "Invalid JSON", "messages": extract_messages(request)}, status=400
        )

    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
        logger.exception("Unexpected error during timesheet autosave")
        return JsonResponse(
            {"error": str(e), "messages": extract_messages(request)}, status=500
        )
