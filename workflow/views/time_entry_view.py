import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib import messages

from workflow.enums import RateType
from workflow.models import Job, JobPricing, Staff, TimeEntry
from workflow.forms import TimeEntryForm, PaidAbsenceForm
from workflow.utils import extract_messages, get_rate_type_label

logger = logging.getLogger(__name__)


"""
View to manage and display timesheet entries for a specific staff member and date.

Purpose:
- Centralizes the logic for rendering the timesheet entry page.
- Dynamically loads staff, jobs, and timesheet data based on the provided date and staff ID.
- Ensures access control and context consistency for the user interface.

Key Features:
- Excludes specific staff members (e.g., app/system users) from being displayed.
- Prepares the context with data necessary for rendering the timesheet entry page.
- Supports navigation between staff members for the same timesheet date.

Attributes:
- `template_name` (str): Path to the template used for rendering the view.
- `EXCLUDED_STAFF_IDS` (list): List of Django staff IDs to be excluded from timesheet views.

Usage:
- Accessed via a URL pattern that includes the date and staff ID as parameters.
- Provides the back-end logic for the `time_entries/timesheet_entry.html` template.
"""
class TimesheetEntryView(TemplateView):
    template_name = "time_entries/timesheet_entry.html" 

    # Excluding app users ID's to avoid them being loaded in timesheet views because they do not have entries 
    EXCLUDED_STAFF_IDS = [
        "a9bd99fa-c9fb-43e3-8b25-578c35b56fa6",
        "b50dd08a-58ce-4a6c-b41e-c3b71ed1d402"
    ]

    """
    Handles GET requests to display the timesheet entry page for a given staff member and date.

    Purpose:
    - Retrieves and validates the date and staff member based on URL parameters.
    - Fetches timesheet entries, open jobs, and navigation details for the UI.
    - Ensures the context contains all data needed to render the page.

    Workflow:
    1. Validates the `date` parameter to ensure it is in the correct format (YYYY-MM-DD).
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
    - Rendered HTML template with the context for the timesheet entry page.

    Error Handling:
    - Raises `ValueError` for invalid date formats.
    - Raises `PermissionError` if the staff member is excluded.
    - Raises `Http404` if the staff member is not found.

    Context:
    - Includes data for the staff member, timesheet entries, open jobs, and navigation links.

    Dependencies:
    - `Staff`, `TimeEntry`, and `Job` models for querying database records.
    - `json.dumps` for serializing data to JSON format.
    - `DjangoJSONEncoder` for handling complex data types.
    - Template: `time_entries/timesheet_entry.html`.

    Notes:
    - The `EXCLUDED_STAFF_IDS` attribute should be updated as needed to reflect changes in app/system users.
    """
    def get(self, request, date, staff_id, *args, **kwargs):
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

        staff_data = {
            "id": staff_member.id,
            "name": staff_member.get_display_full_name(),
            "wage_rate": staff_member.wage_rate,
        }

        time_entries = TimeEntry.objects.filter(
            date=target_date, staff=staff_member
        ).select_related("job_pricing__latest_reality_for_job__client")

        timesheet_data = [
            {
                "id": str(entry.id),
                "job_pricing_id": entry.job_pricing_id,
                "job_number": entry.job_pricing.job.job_number,
                "job_name": entry.job_pricing.job.name,
                "client_name": entry.job_pricing.job.client.name if entry.job_pricing.job.client else "No client!?",
                "description": entry.description or "",
                "hours": float(
                    entry.hours
                ),  # Implicitly assumes one item, which is correct for reality
                "rate_multiplier": float(entry.wage_rate_multiplier),
                "is_billable": entry.is_billable,
                "notes": entry.note or "",
                "timesheet_date": target_date.strftime("%Y-%m-%d"),
                "staff_id": staff_member.id,
            }
            for entry in time_entries
        ]

        open_jobs = Job.objects.filter(
            status__in=["quoting", "approved", "in_progress", "special"]
        ).select_related("client")

        jobs_data = [
            {
                "id": str(job.id),
                "job_number": job.job_number,
                "name": job.name,
                "job_display_name": str(job),
                "client_name": job.client.name if job.client else "NO CLIENT!?",
                "charge_out_rate": float(job.charge_out_rate),
            }
            for job in open_jobs
        ]

        next_staff = Staff.objects.exclude(
            id__in=self.EXCLUDED_STAFF_IDS
        ).filter(
            id__gt=staff_member.id
        ).order_by("id").first()

        if not next_staff:
            next_staff = Staff.objects.exclude(
                id__in=self.EXCLUDED_STAFF_IDS
            ).order_by("id").first()
        
        prev_staff = Staff.objects.exclude(
            id__in=self.EXCLUDED_STAFF_IDS
        ).filter(
            id__lt=staff_member.id
        ).order_by("-id").first()

        if not prev_staff:
            prev_staff = Staff.objects.exclude(
                id__in=self.EXCLUDED_STAFF_IDS
            ).order_by("-id").first()   

        context = {
            "staff_member": staff_member,
            "staff_member_json": json.dumps(staff_data, cls=DjangoJSONEncoder),
            "timesheet_date": target_date.strftime("%Y-%m-%d"),
            "scheduled_hours": float(staff_member.get_scheduled_hours(target_date)),
            "timesheet_entries_json": json.dumps(timesheet_data, cls=DjangoJSONEncoder),
            "jobs_json": json.dumps(jobs_data, cls=DjangoJSONEncoder),
            "next_staff": next_staff,
            "prev_staff": prev_staff,
        }

        return render(request, self.template_name, context)

    """
    Handles POST requests to manage timesheet entries and related actions.

    Purpose:
    - Provides centralized logic for managing timesheet-related AJAX operations.
    - Supports dynamic form loading and submission for timesheet entries.
    - Enables actions for managing paid absences.

    Workflow:
    1. Validates and parses the date from the URL.
    2. Ensures the staff member is authorized and exists in the database.
    3. Determines the requested action (`action` parameter) and processes it:
    - `load_paid_absence`: Renders the form for managing paid absences.
    - `add_paid_absence`: Adds paid absence entries to the timesheet.
    - `load_form`: Loads the timesheet entry form dynamically via AJAX.
    - `submit_form`: Validates and saves the timesheet entry data.
    4. Handles both success and failure responses with appropriate messages.

    Parameters:
    - `request`: The HTTP POST request containing action details and data.
    - `date` (str): The target date for the timesheet, extracted from the URL.
    - `staff_id` (UUID): The ID of the staff member, extracted from the URL.

    Responses:
    - Returns JSON responses for all actions:
    - Success: Includes relevant data for UI updates (e.g., form HTML, entry/job data).
    - Failure: Includes error messages to guide the user.
    
    Error Handling:
    - Raises `ValueError` for invalid date formats.
    - Returns 403 if the staff member is excluded.
    - Returns 404 if the staff member is not found.
    - Handles form validation errors gracefully, returning detailed messages.
    - Handles non-AJAX requests with a general "Invalid request" error.

    Dependencies:
    - Django utilities for JSON and template rendering (`JsonResponse`, `render_to_string`).
    - Custom utilities for extracting messages and formatting rate labels.
    - `TimeEntryForm` and `PaidAbsenceForm` for handling specific actions.

    Usage:
    - Integrated with the timesheet UI to dynamically load forms and process user inputs.
    - Handles backend logic for managing timesheet entries and paid absences.
    """
    def post(self, request, date, staff_id, *args, **kwargs):
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

        if staff_id in self.EXCLUDED_STAFF_IDS:
            messages.error(request, "Access denied for this staff member.")
            return JsonResponse({
                "error": "Access denied for this staff member",
                "messages": extract_messages(request)
                }, status=403)
        
        try:
            staff_member = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            messages.error(request, "Staff member not found.")
            return JsonResponse({
                "error": "Staff member not found",
                "messages": extract_messages(request)
                }, status=404)
        
        action = request.POST.get("action")
        if action == "load_paid_absence":
            return self.load_paid_absence(request)

        if action == "add_paid_absence":
            return self.add_paid_absence(request, staff_member)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            if request.POST.get("action") == "load_form":
                form = TimeEntryForm(
                    staff_member=staff_member, 
                    timesheet_date=target_date
                )
                form_html = render_to_string(
                    "time_entries/timesheet_form.html",
                    {"form": form, "staff_member": staff_member, "target_date": target_date},
                    request=request,
                )
                return JsonResponse({"form_html": form_html})

            elif request.POST.get("action") == "submit_form":
                form = TimeEntryForm(request.POST, staff_member=staff_member)
                if form.is_valid():
                    time_entry = form.save(commit=False)
                    time_entry.staff = staff_member
                    time_entry.date = target_date
                    time_entry.save()

                    messages.success(request, "Timesheet saved successfully")
                    
                   # Return the new entry data for AG Grid with job data so the entry will be fully loaded by the grid
                    entry_data = {
                        "id": str(time_entry.id),
                        "description": time_entry.description or "",
                        "hours": float(time_entry.hours),
                        "rate_multiplier": float(time_entry.wage_rate_multiplier),
                        "rate_type": get_rate_type_label(time_entry.wage_rate_multiplier),
                        "is_billable": time_entry.is_billable,
                        "notes": time_entry.note or "",
                        "timesheet_date": target_date.strftime("%Y-%m-%d"),
                        "staff_id": staff_member.id,
                    }
                    logger.debug("Rate multiplier: %s", entry_data["rate_type"])
                    
                    job = time_entry.job_pricing.job
                    job_data = {
                        "id": str(job.id),
                        "job_number": job.job_number, 
                        "name": job.name,
                        "job_display_name": str(job),
                        "client_name": job.client.name if job.client else "NO CLIENT!?",
                        "charge_out_rate": float(job.charge_out_rate),
                    }

                    return JsonResponse({    
                        "success": True, 
                        "entry": entry_data,
                        "job": job_data,
                        "messages": extract_messages(request),
                    }, status=200)                    

                messages.error(
                    request, 
                    "Please correct the following errors in your time entry submission: " + 
                    ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()])
                )

                return JsonResponse({
                    "success": False, 
                    "errors": form.errors, 
                    "messages": extract_messages(request)
                    }, status=400)                                          

        # Handle non-AJAX POST requests
        messages.error(request, "Invalid request.")
        return JsonResponse({
            "error": "Invalid request", 
            "messages": extract_messages(request)
            }, status=400)    

    """
    Adds paid absence entries to the timesheet.

    Purpose:
    - Automates the creation of time entries for a specified date range, excluding weekends.
    - Associates entries with a predefined virtual job for paid absences.
    - Ensures consistency and validation for staff-related absences.

    Workflow:
    1. Validates and parses the start and end dates from the request.
    2. Excludes invalid ranges where the end date is earlier than the start date.
    3. Iterates through each day in the range, skipping Saturdays and Sundays.
    4. Retrieves the `JobPricing` for the virtual paid absence job.
    5. Creates a `TimeEntry` for each valid weekday, linking it to the staff member and job.
    6. Collects data for each entry to be returned to the front-end.
    7. Returns success or error messages based on the outcome of the operation.

    Parameters:
    - `request`: The HTTP POST request containing the date range and staff details.
    - `staff_member`: The `Staff` object representing the staff member for whom the entries are created.

    Responses:
    - Success: Returns a list of created entries, including their details for UI updates.
    - Error: Returns validation or processing errors (e.g., invalid date range, missing job pricing).

    Error Handling:
    - Validates the date range to ensure `end_date >= start_date`.
    - Skips weekends (Saturday and Sunday) during entry creation.
    - Handles cases where `JobPricing` for the paid absence job cannot be found.
    - Catches and reports errors during entry creation, ensuring partial failures don't halt the process entirely.

    Dependencies:
    - Django's models (`JobPricing`, `TimeEntry`) for database operations.
    - Utility functions (`extract_messages`) for consistent error and success messaging.

    Usage:
    - Triggered via the `post` method in `TimesheetEntryView` when the action is `add_paid_absence`.
    - Enables bulk creation of time entries for predefined absence scenarios, improving efficiency and consistency.

    Notes:
    - Weekends are automatically excluded to reflect typical work schedules.
    - The virtual paid absence job ID (`job_id`) is hardcoded to match the Paid Absence Job, but the form can be updated to manage dynamic special jobs for paid leaves/absences
    """
    def add_paid_absence(self, request, staff_member):
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        job_id = "ce8f9015-2a25-45fe-8441-1749989add05" # Virtual absence job id

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            if end_date < start_date:
                messages.error(request, "End date must be greater than or equal to start date.")
                raise ValueError("End date must be greater than or equal to start date.")
        except ValueError as e:
            return JsonResponse({
                "error": str(e),
                "messages": extract_messages(request)
                }, status=400)
        
        days = (end_date - start_date).days + 1
        entries = []
        for i in range(days):
            entry_date = start_date + timedelta(days=i)

            # Skipping weekends
            if entry_date.weekday() in [5, 6]: 
                continue

            try:
                # Fetching the JobPricing related to the Paid Absence Job
                job_pricing = JobPricing.objects.filter(job_id=job_id).first() # Maybe there's a better way to do it without having to import another model, but it solves the problem
                if not job_pricing:
                            return JsonResponse({
                                "error": "Job pricing for paid absence not found.",
                                "messages": [{"level": "error", "message": "Job pricing for paid absence not found."}]
                            }, status=400)
                
                entry = TimeEntry.objects.create(
                    job_pricing=job_pricing,
                    staff=staff_member,
                    date=entry_date,
                    hours=8,
                    description="Paid Absence",
                    is_billable=False,
                    note="Automatically created leave entry",
                    wage_rate=staff_member.wage_rate,
                    charge_out_rate=job_pricing.job.charge_out_rate,
                    wage_rate_multiplier=1.0
                )

                job = entry.job_pricing.job
                job_data = {
                    "id": str(job.id),
                    "job_number": job.job_number, 
                    "name": job.name,
                    "job_display_name": str(job),
                    "client_name": job.client.name if job.client else "NO CLIENT!?",
                    "charge_out_rate": float(job.charge_out_rate),
                }

                entries.append({
                    "id": str(entry.id),
                    "job_pricing_id": str(entry.job_pricing_id),
                    "job_number": entry.job_pricing.job.job_number,
                    "job_name": entry.job_pricing.job.name,
                    "job_data": job_data,
                    "client": entry.job_pricing.job.client.name if entry.job_pricing.job.client else "Paid Absence",
                    "description": entry.description or "",
                    "hours": float(entry.hours),
                    "rate_multiplier": float(entry.wage_rate_multiplier),
                    "is_billable": entry.is_billable,
                    "notes": entry.note or "",
                    "timesheet_date": entry_date.strftime("%Y-%m-%d"),
                    "staff_id": staff_member.id,
                })

            except Exception as e:
                messages.error(request, f"Error creating paid absence entry: {str(e)}")
                return JsonResponse({
                    "error": str(e),
                    "messages": extract_messages(request)
                    }, status=400)
        
        messages.success(request, "Paid absence entries created successfully")
        return JsonResponse({
            "success": True,
            "entries": entries,
            "messages": extract_messages(request)
            }, status=200)
    
    """
    Loads the paid absence form for rendering in the front-end.

    Purpose:
    - Dynamically generates the HTML for the paid absence form.
    - Provides a seamless user experience by enabling form rendering via AJAX.

    Workflow:
    1. Instantiates the `PaidAbsenceForm` with the data from the request.
    2. Renders the form into an HTML string using the `render_to_string` utility.
    3. Returns a JSON response containing:
    - The rendered form HTML.
    - Success status.
    - Any messages to be displayed to the user.

    Parameters:
    - `request`: The HTTP POST request containing the form data.

    Responses:
    - Success:
    - Includes the rendered HTML for the form (`form_html`).
    - Provides feedback messages to the user if necessary.
    - Error Handling: Assumes basic validation at the form level.

    Dependencies:
    - `PaidAbsenceForm`: The Django form used for capturing paid absence details.
    - `render_to_string`: Utility for converting a template and context into HTML.
    - `extract_messages`: Utility for extracting user feedback messages from the request.

    Usage:
    - Triggered via the `post` method in `TimesheetEntryView` when the action is `load_paid_absence`.
    - Enables dynamic loading of the paid absence form in a modal or similar UI component.

    Notes:
    - Optimized for AJAX-based workflows to improve responsiveness and user experience.
    - Any server-side validation should be handled when the form is submitted (at `add_paid_absence`), not at this stage.
    """
    def load_paid_absence(self, request):
        form = PaidAbsenceForm(request.POST)
        form_html = render_to_string(
            "time_entries/paid_absence_form.html",
            {"form": form},
            request=request
        )

        return JsonResponse({
            "success": True,
            "form_html": form_html,
            "messages": extract_messages(request)
        }, status=200)


"""
Handles autosave requests for timesheet data.

Purpose:
- Automates the saving of timesheet changes, including updates, creations, and deletions.
- Ensures data consistency by validating and processing entries before saving.
- Provides a seamless experience by integrating with AJAX for real-time updates.

Workflow:
1. Parses and validates the request body as JSON.
2. Separates entries to update/create (`time_entries`) and entries to delete (`deleted_entries`).
3. Processes deletions:
   - Removes entries by ID if they exist.
   - Logs and ignores non-existent entries.
4. Processes time entries:
   - Skips incomplete or invalid entries.
   - Updates existing entries by ID.
   - Creates new entries while avoiding duplication.
5. Returns success or error responses with detailed messages.

Parameters:
- `request`: The HTTP POST request containing timesheet data in JSON format.

Responses:
- Success:
  - Includes IDs of updated or created entries.
  - Provides user feedback messages for UI updates.
- Error:
  - Includes error details for invalid data, missing entries, or unexpected issues.

Error Handling:
- Validates JSON format and structure (`time_entries` and `deleted_entries`).
- Handles invalid or missing data gracefully, skipping affected entries.
- Catches unexpected exceptions, logging details for debugging.

Dependencies:
- Django models (`TimeEntry`, `Job`, `Staff`) for database operations.
- Utility functions (`extract_messages`) for consistent user feedback.
- `RateType` for managing wage rate multipliers.

Usage:
- Triggered via an AJAX POST request from the timesheet interface.
- Supports real-time saving of user edits and deletions in the grid.

Notes:
- Designed for efficient bulk processing to minimize server load.
- Prevents duplicate entries by checking for existing records with the same attributes.
- Logs all operations for traceability and debugging.
"""
@require_http_methods(["POST"])
def autosave_timesheet_view(request):
    try:
        logger.debug("Timesheet autosave request received")
        data = json.loads(request.body)
        time_entries = data.get("time_entries", [])
        deleted_entries = data.get("deleted_entries", [])

        logger.debug(f"Number of time entries: {len(time_entries)}")
        logger.debug(f"Number of entries to delete: {len(deleted_entries)}")

        if deleted_entries:
            for entry_id in deleted_entries:
                logger.debug(f"Deleting entry with ID: {entry_id}")

                try:
                    entry = TimeEntry.objects.get(id=entry_id)
                    messages.success(request, f"Timesheet deleted successfully")
                    entry.delete()
                    logger.debug(f"Entry with ID {entry_id} deleted successfully")
                    return JsonResponse({
                        "success": True,
                        "messages": extract_messages(request)
                    }, status=200)

                except TimeEntry.DoesNotExist:
                    logger.error(f"TimeEntry with ID {entry_id} not found for deletion")

        if not time_entries and not deleted_entries:
            logger.error("No valid entries to process")
            messages.info(request, "No changes to save.")
            return JsonResponse({
                "error": "No time entries provided", 
                "messages": extract_messages(request)
                }, status=400)

        updated_entries = []
        for entry_data in time_entries:
            if not entry_data.get("job_number") or not entry_data.get("hours"):
                logger.debug("Skipping incomplete entry: ", entry_data)
                continue

            entry_id = entry_data.get("id")
            
            try:
                hours = Decimal(str(entry_data.get("hours", 0)))
            except (TypeError, ValueError) as e:
                messages.error(request, f"Invalid hours value: {str(e)}")
                return JsonResponse({
                    "error": f"Invalid hours value: {str(e)}", 
                    "messages": extract_messages(request)
                    }, status=400)

            try:
                timesheet_date = entry_data.get("timesheet_date", None)
                if not timesheet_date:
                    logger.error("Missing timesheet_date in entry data")
                    continue  

                target_date = datetime.strptime(timesheet_date, "%Y-%m-%d").date()
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid timesheet_date format: {entry_data.get("timesheet_date")}")
                continue  

            if entry_id and entry_id != 'tempId':
                try:
                    logger.debug(f"Processing entry with ID: {entry_id}")
                    entry = TimeEntry.objects.get(id=entry_id)

                    # Update existing entry
                    entry = TimeEntry.objects.get(id=entry_id)
                    entry.description = entry_data.get("description", "")
                    entry.hours = hours
                    entry.is_billable = entry_data.get("is_billable", True)
                    entry.note = entry_data.get("notes", "")
                    rate_type = entry_data.get("rate_type", RateType.ORDINARY.value)
                    entry.wage_rate_multiplier = RateType(rate_type).multiplier

                    entry.save()
                    messages.success(request, "Existing timesheet saved successfully.")
                    logger.debug("Existing timesheet saved successfully")

                except TimeEntry.DoesNotExist:
                    logger.error(f"TimeEntry with ID {entry_id} not found")

            else:
                # Verify if there's already a registry with same data to avoid creating multiple entries
                job_id = entry_data.get("job_data", {}).get("id")
                description = entry_data.get("description", "").strip()
                hours = Decimal(str(entry_data.get("hours", 0)))

                existing_entry = TimeEntry.objects.filter(
                    job_pricing__job_id=job_id,
                    staff_id=entry_data.get("staff_id"),
                    date=target_date,
                    description=description,
                    hours=hours
                ).first()

                if existing_entry:
                    logger.info(f"Found duplicated entry: {existing_entry.id}")
                    continue 

                # Create new entry - need to get job_pricing
                job = Job.objects.get(id=job_id)
                job_pricing = job.latest_reality_pricing
                staff = Staff.objects.get(id=entry_data.get("staff_id"))

                date_str = entry_data.get("timesheet_date")
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                wage_rate_multiplier = RateType(entry_data["rate_type"]).multiplier
                wage_rate = staff.wage_rate 
                charge_out_rate = entry_data["job_data"]["charge_out_rate"]

                entry = TimeEntry.objects.create(
                    job_pricing=job_pricing,
                    staff_id=entry_data.get("staff_id"),
                    date=target_date,
                    description=description,
                    hours=hours,
                    is_billable=entry_data.get("is_billable", True),
                    note=entry_data.get("notes", ""),
                    wage_rate_multiplier=wage_rate_multiplier,
                    wage_rate=wage_rate,
                    charge_out_rate=charge_out_rate,
                )
                
                updated_entries.append(entry.id)
                entry.save()

                messages.success(request, "Timesheet created successfully.")
                logger.debug("Timesheet created successfully")
                return JsonResponse({
                    "success": True,
                    "messages": extract_messages(request),
                    "entry_id": entry.id
                }, status=200)

        return JsonResponse({
            "success": True,
            "updated_entries": updated_entries,
            "messages": extract_messages(request)
        }, status=200)

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        messages.error(request, "Failed to parse JSON")
        return JsonResponse({
            "error": "Invalid JSON",
            "messages": extract_messages(request)
            }, status=400)

    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
        logger.exception("Unexpected error during timesheet autosave")
        return JsonResponse({
            "error": str(e),
            "messages": extract_messages(request)
            }, status=500)
