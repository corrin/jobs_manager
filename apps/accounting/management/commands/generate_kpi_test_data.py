import calendar
import datetime
import random
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounting.utils import get_nz_tz
from apps.accounts.models import Staff
from apps.client.models import Client
from apps.job.enums import JobPricingStage
from apps.job.models import AdjustmentEntry, Job, JobPricing, MaterialEntry
from apps.timesheet.models import TimeEntry
from apps.workflow.models import CompanyDefaults

STOCK_CLIENT_ID = "00000000-0000-0000-0000-000000000001"
# TODO: Change to a proper import: Client.get_shop_client_id()


class Command(BaseCommand):
    help = (
        "Generate mock time entries for the current month to display KPI calendar data"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete all mock time entries created by this script",
        )
        parser.add_argument(
            "--month",
            type=int,
            help="Month to generate data for (1-12), defaults to current month",
        )
        parser.add_argument(
            "--year",
            type=int,
            help="Year to generate data for, defaults to current year",
        )
        parser.add_argument(
            "--days",
            type=str,
            help=(
                'Days pattern (good:medium:bad) e.g. "10:5:5" for '
                "10 good, 5 medium, 5 bad days"
            ),
            default="10:6:4",
        )

    def handle(self, *args, **options):
        delete_mode = options.get("delete", False)

        if delete_mode:
            self._delete_mock_data()
            return

        # Get month/year to generate data for and ensure they are not None
        today = timezone.now().date()

        # Get and validate year value
        year = options.get("year")
        if year is None:
            year = today.year

        # Get and validate month value
        month = options.get("month")
        if month is None:
            month = today.month

        # Log the values we're using
        self.stdout.write(
            self.style.SUCCESS(
                f"Generating data for {calendar.month_name[month]} {year}"
            )
        )

        # Parse days pattern
        days_pattern = options.get("days", "10:6:4")
        try:
            good_days, medium_days, bad_days = map(int, days_pattern.split(":"))
        except ValueError:
            self.stdout.write(
                self.style.ERROR(
                    (
                        "Invalid days pattern format. Use format "
                        '"good:medium:bad" e.g. "10:5:5"'
                    )
                )
            )
            return

        # Generate the data - explicitly pass the values instead of
        # relying on options dictionary
        self._generate_mock_data(
            int(year), int(month), good_days, medium_days, bad_days
        )

    def _delete_mock_data(self):
        """Delete all mock time entries created by this script"""
        try:
            # Find entries with note containing our marker
            mock_time_entries = TimeEntry.objects.filter(
                note__contains="Auto-generated KPI test data"
            )
            time_count = mock_time_entries.count()
            mock_time_entries.delete()

            mock_material_entries = MaterialEntry.objects.filter(
                comments__contains="Auto-generated KPI test data"
            )
            material_count = mock_material_entries.count()
            mock_material_entries.delete()

            mock_adjustment_entries = AdjustmentEntry.objects.filter(
                comments__contains="Auto-generated KPI test data"
            )
            adjustment_count = mock_adjustment_entries.count()
            mock_adjustment_entries.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted mock entries:\n"
                    f"- Time entries: {time_count}\n"
                    f"- Material entries: {material_count}\n"
                    f"- Adjustment entries: {adjustment_count}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error deleting mock data: {str(e)}"))

    def _generate_mock_data(self, year, month, good_days, medium_days, bad_days):
        """Generate mock time entries for the specified month"""
        # Validate inputs right at the beginning
        if year is None or month is None:
            self.stdout.write(
                self.style.ERROR(f"Invalid year ({year}) or month ({month}) values")
            )
            return

        try:
            # Force conversion to integers to prevent type issues
            year = int(year)
            month = int(month)

            # Log what we're processing for debugging
            self.stdout.write(f"Processing data for {year}-{month}")

            # Get company defaults to know thresholds
            company_defaults = CompanyDefaults.objects.first()
            if not company_defaults:
                self.stdout.write(self.style.ERROR("Company defaults not found"))
                return

            green_threshold = float(company_defaults.billable_threshold_green or 45)
            amber_threshold = float(company_defaults.billable_threshold_amber or 30)

            # Get staff members (exclude admin users)
            staff_members = Staff.objects.filter(is_staff=False)
            if not staff_members.exists():
                self.stdout.write(self.style.ERROR("No staff members found"))
                return

            # First, let's ensure we have shop and regular jobs
            self._ensure_job_data_exists()

            # Get valid job pricings to assign time entries to
            job_pricings = self._get_job_pricings(relaxed=True)
            if not job_pricings:
                self.stdout.write(self.style.ERROR("No job pricings found"))
                return

            # Get shop job pricings for non-billable work (using client_id instead
            # of shop_job)
            shop_job_pricings = [
                jp for jp in job_pricings if str(jp.job.client_id) == STOCK_CLIENT_ID
            ]

            # Regular job pricings for billable work
            regular_job_pricings = [
                jp
                for jp in job_pricings
                if str(jp.job.client_id) != "00000000-0000-0000-0000-000000000001"
            ]

            if not shop_job_pricings:
                self.stdout.write(
                    self.style.WARNING("No shop job pricings found, creating some...")
                )
                shop_job_pricings = self._create_shop_job_pricings()

            if not regular_job_pricings:
                self.stdout.write(
                    self.style.WARNING(
                        "No regular job pricings found, creating some..."
                    )
                )
                regular_job_pricings = self._create_regular_job_pricings()

            # Create a list of working days in the month (skip weekends)
            working_days = self._get_working_days(year, month)
            if not working_days:
                self.stdout.write(
                    self.style.ERROR("No working days found for the specified month")
                )
                return

            # Assign performance categories to days (green, amber, red)
            day_categories = self._categorize_days(
                working_days, good_days, medium_days, bad_days
            )

            with transaction.atomic():
                total_entries = 0

                for day_date, category in day_categories.items():
                    # Determine target billable hours based on category
                    if category == "green":
                        target_billable = (
                            green_threshold * 1.1
                        )  # Slightly above threshold
                    elif category == "amber":
                        target_billable = (
                            green_threshold + amber_threshold
                        ) / 2  # Between thresholds
                    else:  # red
                        target_billable = amber_threshold * 0.8  # Below amber threshold

                    # Create time entries for this day
                    entries_created = self._create_day_entries(
                        day_date,
                        staff_members,
                        regular_job_pricings,
                        shop_job_pricings,
                        target_billable,
                        category,
                    )

                    total_entries += entries_created

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created {total_entries} mock entries for "
                    f"{calendar.month_name[month]} {year}\n"
                    f"- Green days: {good_days}\n"
                    f"- Amber days: {medium_days}\n"
                    f"- Red days: {bad_days}\n"
                    f"KPI thresholds: Green ≥ {green_threshold}, "
                    f"Amber ≥ {amber_threshold}"
                )
            )

        except Exception as e:
            import traceback

            self.stdout.write(
                self.style.ERROR(
                    f"Error generating mock data: {str(e)}\n{traceback.format_exc()}"
                )
            )

    def _ensure_job_data_exists(self):
        """Verifies and creates default jobs if necessary"""
        # Check if a client for shop jobs exists
        shop_client_exists = False
        try:
            # Check if shop client exists by hardcoded UUID
            shop_client_exists = Client.objects.filter(
                pk="00000000-0000-0000-0000-000000000001"
            ).exists()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error checking shop client existence: {str(e)}")
            )
            shop_client_exists = False

        if not shop_client_exists:
            self.stdout.write(
                self.style.WARNING(
                    "Shop client not found. Please run "
                    "`python manage.py create_shop_jobs` first"
                )
            )
            self.stdout.write(self.style.WARNING("Creating dummy data for testing..."))
            self._create_test_data()

    def _create_test_data(self):
        """Create minimal test data for the command to run"""

        try:
            # Import models here to avoid circular imports
            from apps.client.models import Client
            from apps.job.models import Job

            # Create company defaults if needed
            if not CompanyDefaults.objects.exists():
                CompanyDefaults.objects.create(
                    pk="Test Company",
                    charge_out_rate=Decimal("105.00"),
                    wage_rate=Decimal("35.00"),
                    time_markup=Decimal("0.30"),
                    materials_markup=Decimal("0.20"),
                    billable_threshold_green=45,
                    billable_threshold_amber=30,
                    shop_hours_target_percentage=20,
                )

            # Create a shop client if it doesn't exist
            shop_client, created = Client.objects.get_or_create(
                pk="00000000-0000-0000-0000-000000000001",
                defaults={"name": "Test Shop", "email": "test@example.com"},
            )

            # Create a test client for billable jobs
            test_client, created = Client.objects.get_or_create(
                name="Test Client", defaults={"email": "client@example.com"}
            )

            # Create some shop jobs if needed
            shop_job_names = [
                "Business Development",
                "Bench - busy work",
                "Worker Admin",
                "Annual Leave",
            ]
            for name in shop_job_names:
                if not Job.objects.filter(name=name).exists():
                    job = Job(
                        name=name,
                        client=shop_client,
                        description=f"Test {name}",
                        status="special",
                        job_number=random.randint(1000, 9999),
                        charge_out_rate=Decimal("0.00"),
                    )
                    job.save()
                    self.stdout.write(f"Created shop job: {name}")

            # Create some regular jobs if needed
            regular_job_names = ["Project Alpha", "Project Beta", "Maintenance Work"]
            for name in regular_job_names:
                if not Job.objects.filter(name=name).exists():
                    job = Job(
                        name=name,
                        client=test_client,
                        description=f"Test {name}",
                        status="in_progress",
                        job_number=random.randint(1000, 9999),
                        charge_out_rate=Decimal("105.00"),
                    )
                    job.save()
                    self.stdout.write(f"Created regular job: {name}")

        except Exception as e:
            import traceback

            self.stdout.write(self.style.ERROR(f"Error creating test data: {str(e)}"))
            self.stdout.write(self.style.ERROR(traceback.format_exc()))

    def _create_shop_job_pricings(self):
        """Create job pricings for shop jobs if none exist"""
        # Get shop jobs by querying the client_id directly
        shop_jobs = Job.objects.filter(client_id="00000000-0000-0000-0000-000000000001")
        if not shop_jobs.exists():
            # Try alternative method using client name
            try:
                shop_jobs = Job.objects.filter(client__name__icontains="Shop")
            except Exception:
                pass

        shop_job_pricings = []
        for job in shop_jobs:
            # Get or create reality pricing for the job
            job_pricing, created = JobPricing.objects.get_or_create(
                job=job,
                pricing_stage=JobPricingStage.REALITY,
                defaults={"is_historical": False},
            )
            shop_job_pricings.append(job_pricing)

        return shop_job_pricings

    def _create_regular_job_pricings(self):
        """Create job pricings for regular jobs if none exist"""
        # Get regular jobs by excluding shop client id
        regular_jobs = Job.objects.exclude(
            client_id="00000000-0000-0000-0000-000000000001"
        )
        if not regular_jobs.exists():
            try:
                regular_jobs = Job.objects.exclude(client__name__icontains="Shop")
            except Exception:
                pass

        regular_job_pricings = []
        for job in regular_jobs:
            # Get or create reality pricing for the job
            job_pricing, created = JobPricing.objects.get_or_create(
                job=job,
                pricing_stage=JobPricingStage.REALITY,
                defaults={"is_historical": False},
            )
            regular_job_pricings.append(job_pricing)

        return regular_job_pricings

    def _get_working_days(self, year, month):
        """Get all working days (Mon-Fri) in the specified month"""
        # Double-check inputs to prevent None values
        if year is None or month is None:
            self.stdout.write(
                self.style.ERROR(f"Invalid year ({year}) or month ({month}) values")
            )
            return []

        # Convert to int to ensure correct types
        try:
            year = int(year)
            month = int(month)

            # Validate month range
            if not 1 <= month <= 12:
                self.stdout.write(
                    self.style.ERROR(
                        f"Month value must be between 1 and 12, got {month}"
                    )
                )
                return []

            # Get the days in the month
            _, last_day = calendar.monthrange(year, month)
            working_days = []

            for day in range(1, last_day + 1):
                day_date = date(year, month, day)
                # Skip weekends (5=Saturday, 6=Sunday)
                if day_date.weekday() < 5:
                    working_days.append(day_date)

            return working_days
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error calculating working days: {e}"))
            return []

    def _categorize_days(self, working_days, good_days, medium_days, bad_days):
        """Assign performance categories to working days"""
        if good_days + medium_days + bad_days != len(working_days):
            # Adjust to match available working days
            total = good_days + medium_days + bad_days
            ratio = len(working_days) / total

            good_days = int(good_days * ratio)
            medium_days = int(medium_days * ratio)
            bad_days = len(working_days) - good_days - medium_days

            self.stdout.write(
                self.style.WARNING(
                    f"Adjusted days pattern to match {len(working_days)} working days: "
                    f"{good_days} good, {medium_days} medium, {bad_days} bad"
                )
            )

        # Shuffle days to randomize
        random_days = working_days.copy()
        random.shuffle(random_days)

        # Assign categories
        categories = {}
        for day in random_days[:good_days]:
            categories[day] = "green"
        for day in random_days[good_days : good_days + medium_days]:
            categories[day] = "amber"
        for day in random_days[good_days + medium_days :]:
            categories[day] = "red"

        return categories

    def _get_job_pricings(self, relaxed=False):
        """Get active job pricings with reality stage"""
        qs = JobPricing.objects.filter(pricing_stage=JobPricingStage.REALITY)
        if relaxed:
            qs = qs.filter(
                job__status__in=[
                    "approved",
                    "in_progress",
                    "special",
                    "quoting",
                    "on_hold",
                ]
            )
        else:
            qs = qs.filter(job__status__in=["approved", "in_progress", "special"])
        return list(qs)

    @staticmethod
    def _nz_random_dt(day_date: date) -> datetime.datetime:
        """
        Returns a random time (09-17 h) of the day in NZ timezone
        """
        hh = random.randint(9, 16)
        mm = random.randint(0, 59)
        naive = datetime.datetime.combine(day_date, datetime.time(hh, mm))
        return timezone.make_aware(naive, get_nz_tz())

    @staticmethod
    def _rand_decimal(low, high, ndigits=2):
        """Returns a rounded Decimal between low and high (accepts float or Decimal)."""
        # cast to float before uniform()
        low_f, high_f = float(low), float(high)
        value = random.uniform(low_f, high_f)
        return Decimal(str(round(value, ndigits)))

    def _create_material_entries(self, day_date, job_pricings, category):
        """
        Creates MaterialEntry(s) for the day. Guarantees at least 1.
        Returns the number created.
        """
        cat_cfg = {
            "green": dict(prob=0.9, cnt=(2, 6), cost=(40, 350), mark=(1.25, 1.55)),
            "amber": dict(prob=0.7, cnt=(1, 4), cost=(25, 300), mark=(1.15, 1.40)),
            "red": dict(prob=0.5, cnt=(1, 3), cost=(15, 220), mark=(1.05, 1.25)),
        }[category]

        created = 0

        # Determine how many materials to create based on category
        num_materials = random.randint(*cat_cfg["cnt"])

        # Get job pricings that have time entries on this date, if any
        jobs_with_time = []
        for jp in job_pricings:
            if TimeEntry.objects.filter(job_pricing=jp, date=day_date).exists():
                jobs_with_time.append(jp)

        # Use jobs with time entries if available, otherwise use random selection
        target_jobs = (
            jobs_with_time
            if jobs_with_time
            else random.sample(
                job_pricings,
                min(len(job_pricings), max(1, int(len(job_pricings) * 0.3))),
            )
        )

        if target_jobs:
            # Create materials distributed among target jobs
            for _ in range(num_materials):
                jp = random.choice(target_jobs)
                markup_lo, markup_hi = cat_cfg["mark"]
                unit_cost = self._rand_decimal(*cat_cfg["cost"])
                markup = random.uniform(markup_lo, markup_hi)
                unit_rev = (unit_cost * Decimal(str(markup))).quantize(Decimal("1.00"))

                MaterialEntry.objects.create(
                    job_pricing=jp,
                    description=f"MAT {random.randint(1000, 9999)}",
                    unit_cost=unit_cost,
                    unit_revenue=unit_rev,
                    quantity=random.randint(1, 7),
                    comments=f"Auto-generated KPI test data ({category})",
                    accounting_date=day_date,
                    created_at=self._nz_random_dt(day_date),
                )
                created += 1

        # Create a fallback entry if nothing was created
        if created == 0 and job_pricings:
            jp = random.choice(job_pricings)
            MaterialEntry.objects.create(
                job_pricing=jp,
                description="Fallback material",
                unit_cost=Decimal("50.00"),
                unit_revenue=Decimal("75.00"),
                quantity=1,
                comments=f"Auto-generated KPI test data ({category})",
                accounting_date=day_date,
                created_at=self._nz_random_dt(day_date),
            )
            created = 1

        return created

    def _create_adjustment_entries(self, day_date, job_pricings, category):
        """
        Creates AdjustmentEntry(s) for the day. Guarantees at least 1.
        Returns the number created.
        """
        cat_cfg = {
            "green": dict(prob=0.5, price=(-300, 700), cost=(-400, 150)),
            "amber": dict(prob=0.4, price=(-400, 500), cost=(-300, 200)),
            "red": dict(prob=0.3, price=(-500, 300), cost=(-250, 250)),
        }[category]

        created = 0

        # Get job pricings that have time entries on this date, if any
        jobs_with_time = []
        for jp in job_pricings:
            if TimeEntry.objects.filter(job_pricing=jp, date=day_date).exists():
                jobs_with_time.append(jp)

        # Use jobs with time entries if available, otherwise use random selection
        target_jobs = (
            jobs_with_time
            if jobs_with_time
            else random.sample(
                job_pricings,
                min(len(job_pricings), max(1, int(len(job_pricings) * 0.2))),
            )
        )

        # Create 1-2 adjustment entries based on category
        num_adjustments = 1 if random.random() > cat_cfg["prob"] else 2

        if target_jobs:
            # Create adjustments for the determined number
            for _ in range(num_adjustments):
                jp = random.choice(target_jobs)
                price_adj = self._rand_decimal(*cat_cfg["price"])
                cost_adj = (
                    self._rand_decimal(*cat_cfg["cost"])
                    if random.random() < 0.8
                    else Decimal("0.00")
                )

                AdjustmentEntry.objects.create(
                    job_pricing=jp,
                    description=f"ADJ {random.randint(1000, 9999)}",
                    price_adjustment=price_adj,
                    cost_adjustment=cost_adj,
                    comments=f"Auto-generated KPI test data ({category})",
                    accounting_date=day_date,
                    created_at=self._nz_random_dt(day_date),
                )
                created += 1

        # Create a fallback entry if nothing was created
        if created == 0 and job_pricings:
            jp = random.choice(job_pricings)
            AdjustmentEntry.objects.create(
                job_pricing=jp,
                description="Fallback adjustment",
                price_adjustment=self._rand_decimal(*cat_cfg["price"]),
                cost_adjustment=(
                    self._rand_decimal(*cat_cfg["cost"])
                    if random.random() < 0.7
                    else Decimal("0.00")
                ),
                comments=f"Auto-generated KPI test data ({category})",
                accounting_date=day_date,
                created_at=self._nz_random_dt(day_date),
            )
            created = 1

        return created

    def _create_day_entries(
        self,
        day_date,
        staff_members,
        regular_job_pricings,
        shop_job_pricings,
        target_billable,
        category,
    ):
        """Create time, material and adjustment entries for a specific day"""
        entries_created = 0
        staff_list = list(staff_members)
        random.shuffle(staff_list)

        # Determine billable percentage based on category
        if category == "green":
            billable_pct = random.uniform(0.7, 0.85)  # 70-85% billable
        elif category == "amber":
            billable_pct = random.uniform(0.55, 0.7)  # 55-70% billable
        else:  # red
            billable_pct = random.uniform(0.3, 0.55)  # 30-55% billable

        # Create entries for each staff
        for staff in staff_list:
            try:
                # Safely get scheduled hours with fallback
                try:
                    scheduled_hours = float(staff.get_scheduled_hours(day_date) or 0)
                except (TypeError, AttributeError, ValueError):
                    scheduled_hours = (
                        8.0  # Default to 8 hours if we can't get scheduled hours
                    )

                if scheduled_hours <= 0:
                    continue  # Skip staff not scheduled to work

                # Split hours between billable and non-billable
                billable_hours = scheduled_hours * billable_pct
                non_billable_hours = scheduled_hours - billable_hours

                # Create billable entries if we have billable hours and regular jobs
                if billable_hours > 0 and regular_job_pricings:
                    # Distribute billable hours across 1-3 jobs
                    num_jobs = min(random.randint(1, 3), len(regular_job_pricings))
                    job_pricings = random.sample(regular_job_pricings, num_jobs)

                    # Split hours evenly with some variation
                    hours_per_job = [billable_hours / num_jobs] * num_jobs
                    for i in range(len(hours_per_job) - 1):
                        adjustment = random.uniform(-0.5, 0.5)
                        hours_per_job[i] += adjustment
                        hours_per_job[-1] -= adjustment

                    for i, jp in enumerate(job_pricings):
                        hours = max(
                            0.25, round(hours_per_job[i], 2)
                        )  # Minimum 15 minutes

                        # Get a safe charge_out_rate value
                        charge_out_rate = getattr(jp.job, "charge_out_rate", None)
                        if charge_out_rate is None:
                            charge_out_rate = (
                                CompanyDefaults.objects.first().charge_out_rate
                            )

                        # Create the time entry
                        TimeEntry.objects.create(
                            job_pricing=jp,
                            staff=staff,
                            date=day_date,
                            hours=Decimal(str(hours)),
                            description=f"Work on {jp.job.name}",
                            is_billable=True,
                            wage_rate=staff.wage_rate
                            or Decimal("35.00"),  # Fallback wage rate
                            charge_out_rate=charge_out_rate,
                            wage_rate_multiplier=Decimal("1.00"),
                            note=f"Auto-generated KPI test data ({category} day)",
                        )
                        entries_created += 1

                # Create non-billable entries if we have non-billable hours and
                # shop jobs
                if non_billable_hours > 0 and shop_job_pricings:
                    # Pick 1-2 shop jobs
                    num_jobs = min(random.randint(1, 2), len(shop_job_pricings))
                    job_pricings = random.sample(shop_job_pricings, num_jobs)

                    # Split hours evenly with some variation
                    hours_per_job = [non_billable_hours / num_jobs] * num_jobs
                    for i in range(len(hours_per_job) - 1):
                        adjustment = random.uniform(-0.3, 0.3)
                        hours_per_job[i] += adjustment
                        hours_per_job[-1] -= adjustment

                    for i, jp in enumerate(job_pricings):
                        hours = max(
                            0.25, round(hours_per_job[i], 2)
                        )  # Minimum 15 minutes

                        # Create the time entry
                        TimeEntry.objects.create(
                            job_pricing=jp,
                            staff=staff,
                            date=day_date,
                            hours=Decimal(str(hours)),
                            description=f"Internal work - {jp.job.name}",
                            is_billable=False,
                            wage_rate=staff.wage_rate
                            or Decimal("35.00"),  # Fallback wage rate
                            charge_out_rate=Decimal("0.00"),
                            wage_rate_multiplier=Decimal("1.00"),
                            note=f"Auto-generated KPI test data ({category} day)",
                        )
                        entries_created += 1

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Error creating entries for {staff}: {e}")
                )
                continue  # Skip to next staff member on error

        material_entries_created = self._create_material_entries(
            day_date, regular_job_pricings, category
        )
        entries_created += material_entries_created

        adjustment_entries_created = self._create_adjustment_entries(
            day_date, regular_job_pricings, category
        )
        entries_created += adjustment_entries_created

        return entries_created
