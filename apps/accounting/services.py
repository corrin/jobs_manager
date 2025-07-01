import calendar
import datetime
from datetime import date, timedelta
from decimal import Decimal
from logging import getLogger
from typing import Any, Dict, List, Tuple

import holidays
from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.utils import timezone

from apps.accounting.utils import get_nz_tz
from apps.accounts.utils import get_excluded_staff
from apps.client.models import Client
from apps.job.enums import JobPricingStage
from apps.job.models import AdjustmentEntry, MaterialEntry
from apps.timesheet.models import TimeEntry
from apps.workflow.models import CompanyDefaults

logger = getLogger(__name__)


class KPIService:
    """
    Service responsible for calculating and providing KPI metrics for reports.
    All business logic related to KPIs shall be implemented here.
    """

    nz_timezone = get_nz_tz()
    shop_client_id: str = None  # Will be set on first access

    @classmethod
    def _ensure_shop_client_id(cls):
        """Ensure shop_client_id is set, initialize if needed"""
        if cls.shop_client_id is None:
            cls.shop_client_id = Client.get_shop_client_id()

    @staticmethod
    def get_company_thresholds() -> Dict[str, float]:
        """
        Gets KPI thresholds based on CompanyDefaults

        Returns:
            Dict containing thresholds for KPI metrics
        """
        logger.info("Retrieving company thresholds for KPI calculations")
        try:
            company_defaults: CompanyDefaults = CompanyDefaults.objects.first()
            thresholds = {
                "billable_threshold_green": float(
                    company_defaults.billable_threshold_green
                ),
                "billable_threshold_amber": float(
                    company_defaults.billable_threshold_amber
                ),
                "daily_gp_target": float(company_defaults.daily_gp_target),
                "shop_hours_target": float(
                    company_defaults.shop_hours_target_percentage
                ),
            }
            logger.debug(f"Retrieved thresholds: {thresholds}")
            return thresholds
        except Exception as e:
            logger.error(f"Error retrieving company defaults: {str(e)}")
            raise

    @staticmethod
    def _process_entries(
        entries: Dict, revenue_key="revenue", cost_key="cost"
    ) -> Dict[datetime.date, Dict]:
        """
        Segregates entries by date based on the provided Dict
        """
        entries_by_date = {
            entry["local_date"]: {
                "revenue": entry.get(revenue_key) or 0,
                "cost": entry.get(cost_key) or 0,
            }
            for entry in entries
        }
        return entries_by_date

    @classmethod
    def _get_holidays(cls, year, month=None):
        """
        Gets New Zealand holidays for a specific year and month.

        Args:
            year: The year to get holidays for
            month: Optional month (1-12) to filter holidays

        Returns:
            Set of dates that are holidays
        """
        nz_holidays = holidays.country_holidays("NZ", years=year)

        if month:
            return {
                date: name for date, name in nz_holidays.items() if date.month == month
            }
        return dict(nz_holidays)

    @classmethod
    def get_month_days_range(cls, year: int, month: int) -> Tuple[date, date, int]:
        """
        Gets the daily range for a specific month.

        Args:
            year: calendar year
            month: calendar month (1-12)

        Returns:
            Tuple containing initial date, final date and number of days of the month
        """
        logger.info(f"Calculating date range for year={year}, month={month}")
        _, num_days = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        logger.debug(
            f"Date range: {start_date} to {end_date}, days in month: {num_days}"
        )
        return start_date, end_date, num_days

    @staticmethod
    def _get_color(
        value: float | Decimal, green_threshold: float, amber_threshold: float
    ) -> str:
        if value >= green_threshold:
            return "green"
        if value >= amber_threshold:
            return "amber"
        return "red"

    @classmethod
    def get_job_breakdown_for_date(cls, target_date: date) -> List[Dict[str, Any]]:
        """
        Get job-level profit breakdown for a specific date

        Args:
            target_date: The date to get job breakdown for

        Returns:
            List of job breakdowns with profit details
        """

        cls._ensure_shop_client_id()
        excluded_staff_ids = get_excluded_staff()
        # Get time entries for the date
        time_entries = (
            TimeEntry.objects.filter(
                date=target_date, job_pricing__pricing_stage=JobPricingStage.REALITY
            )
            .exclude(staff_id__in=excluded_staff_ids)
            .select_related("job_pricing__job")
        )

        # Get material entries for the date
        timezone.make_aware(
            datetime.datetime.combine(target_date, datetime.time.min), cls.nz_timezone
        )
        timezone.make_aware(
            datetime.datetime.combine(target_date, datetime.time.max), cls.nz_timezone
        )

        material_entries = MaterialEntry.objects.filter(
            accounting_date=target_date,
            job_pricing__pricing_stage=JobPricingStage.REALITY,
        ).select_related("job_pricing__job")

        adjustment_entries = AdjustmentEntry.objects.filter(
            accounting_date=target_date,
            job_pricing__pricing_stage=JobPricingStage.REALITY,
        ).select_related("job_pricing__job")

        # Group by job
        job_data = {}

        # Process time entries
        for entry in time_entries:
            job = entry.job_pricing.job
            job_number = job.job_number

            if job_number not in job_data:
                job_data[job_number] = {
                    "job_id": str(job.id),
                    "job_number": job_number,
                    "job_display_name": job.job_display_name,
                    "labour_revenue": 0,
                    "labour_cost": 0,
                    "material_revenue": 0,
                    "material_cost": 0,
                    "adjustment_revenue": 0,
                    "adjustment_cost": 0,
                }

            if entry.is_billable and str(job.client_id) != cls.shop_client_id:
                job_data[job_number]["labour_revenue"] += float(
                    entry.hours * entry.charge_out_rate
                )
            job_data[job_number]["labour_cost"] += float(entry.hours * entry.wage_rate)

        # Process material entries
        for entry in material_entries:
            job = entry.job_pricing.job
            job_number = job.job_number

            if job_number not in job_data:
                job_data[job_number] = {
                    "job_id": str(job.id),
                    "job_number": job_number,
                    "job_display_name": job.job_display_name,
                    "labour_revenue": 0,
                    "labour_cost": 0,
                    "material_revenue": 0,
                    "material_cost": 0,
                    "adjustment_revenue": 0,
                    "adjustment_cost": 0,
                }

            job_data[job_number]["material_revenue"] += float(
                entry.unit_revenue * entry.quantity
            )
            job_data[job_number]["material_cost"] += float(
                entry.unit_cost * entry.quantity
            )

        # Process adjustment entries
        for entry in adjustment_entries:
            job = entry.job_pricing.job
            job_number = job.job_number

            if job_number not in job_data:
                job_data[job_number] = {
                    "job_id": str(job.id),
                    "job_number": job_number,
                    "job_display_name": job.job_display_name,
                    "labour_revenue": 0,
                    "labour_cost": 0,
                    "material_revenue": 0,
                    "material_cost": 0,
                    "adjustment_revenue": 0,
                    "adjustment_cost": 0,
                }

            job_data[job_number]["adjustment_revenue"] += float(
                entry.price_adjustment or 0
            )
            job_data[job_number]["adjustment_cost"] += float(entry.cost_adjustment or 0)

        # Calculate profits and return sorted list
        result = []
        for job_number, data in job_data.items():
            labour_profit = data["labour_revenue"] - data["labour_cost"]
            material_profit = data["material_revenue"] - data["material_cost"]
            adjustment_profit = data["adjustment_revenue"] - data["adjustment_cost"]
            total_profit = labour_profit + material_profit + adjustment_profit

            result.append(
                {
                    "job_id": data["job_id"],
                    "job_number": job_number,
                    "job_display_name": data["job_display_name"],
                    "labour_profit": labour_profit,
                    "material_profit": material_profit,
                    "adjustment_profit": adjustment_profit,
                    "total_profit": total_profit,
                }
            )

        # Sort by total profit descending
        result.sort(key=lambda x: x["total_profit"], reverse=True)
        return result

    @classmethod
    def get_calendar_data(cls, year: int, month: int) -> Dict[str, Any]:
        """
        Gets all KPI data for a specific month.

        Args:
            year: calendar year
            month: calendar month (1-12)

        Returns:
            Dict containing calendar data, monthly totals and threshold informations
        """
        logger.info(f"Generating KPI calendar data for {year}-{month}")

        cls._ensure_shop_client_id()
        thresholds = cls.get_company_thresholds()
        logger.debug(
            f"Using thresholds: green={thresholds['billable_threshold_green']}, "
            f"amber={thresholds['billable_threshold_amber']}"
        )

        start_date, end_date, _ = cls.get_month_days_range(year, month)
        excluded_staff_ids = get_excluded_staff()
        logger.debug(f"Excluded staff IDs: {excluded_staff_ids}")

        calendar_data = {}
        monthly_totals: Dict[str, float] = {
            "billable_hours": 0,
            "total_hours": 0,
            "shop_hours": 0,
            "gross_profit": 0,
            "days_green": 0,
            "days_amber": 0,
            "days_red": 0,
            "labour_green_days": 0,
            "labour_amber_days": 0,
            "labour_red_days": 0,
            "profit_green_days": 0,
            "profit_amber_days": 0,
            "profit_red_days": 0,
            "working_days": 0,
            "elapsed_workdays": 0,
            "remaining_workdays": 0,
            # The following are internal
            "time_revenue": 0,
            "material_revenue": 0,
            "adjustment_revenue": 0,
            "staff_cost": 0,
            "material_cost": 0,
            "adjustment_cost": 0,
            "material_profit": 0,
            "adjustment_profit": 0,
        }

        decimal_field = DecimalField(max_digits=10, decimal_places=2)
        # Process data of the day - ONLY reality entries
        time_entries_by_date = {
            entry["date"]: entry
            for entry in TimeEntry.objects.filter(
                date__range=[start_date, end_date],
                job_pricing__pricing_stage=JobPricingStage.REALITY,
            )
            .exclude(staff_id__in=excluded_staff_ids)
            .values("date")
            .annotate(
                total_hours=Sum("hours", output_field=decimal_field),
                billable_hours=Sum(
                    Case(
                        When(
                            is_billable=True,
                            then=Case(
                                When(
                                    job_pricing__job__client_id=cls.shop_client_id,
                                    then=Value(0, output_field=decimal_field),
                                ),
                                default="hours",
                            ),
                        ),
                        default=Value(0, output_field=decimal_field),
                    ),
                    output_field=decimal_field,
                ),
                time_revenue=Sum(
                    Case(
                        When(
                            is_billable=True,
                            then=Case(
                                When(
                                    job_pricing__job__client_id=cls.shop_client_id,
                                    then=Value(0, output_field=decimal_field),
                                ),
                                default=F("hours") * F("charge_out_rate"),
                            ),
                        ),
                        default=Value(0, output_field=decimal_field),
                    ),
                    output_field=decimal_field,
                ),
                shop_hours=Sum(
                    Case(
                        When(
                            job_pricing__job__client_id=cls.shop_client_id, then="hours"
                        ),
                        default=Value(0, output_field=decimal_field),
                    ),
                    output_field=decimal_field,
                ),
                staff_cost=Sum(F("hours") * F("wage_rate"), output_field=decimal_field),
            )
        }

        timezone.make_aware(
            datetime.datetime.combine(start_date, datetime.time.min), cls.nz_timezone
        )
        timezone.make_aware(
            datetime.datetime.combine(end_date, datetime.time.max), cls.nz_timezone
        )

        material_entries = (
            MaterialEntry.objects.filter(
                accounting_date__range=[start_date, end_date],
                job_pricing__pricing_stage=JobPricingStage.REALITY,
            )
            .annotate(local_date=F("accounting_date"))
            .values("local_date")
            .annotate(
                revenue=Sum(
                    F("unit_revenue") * F("quantity"), output_field=decimal_field
                ),
                cost=Sum(F("unit_cost") * F("quantity"), output_field=decimal_field),
            )
        )

        adjustment_entries = (
            AdjustmentEntry.objects.filter(
                accounting_date__range=[start_date, end_date],
                job_pricing__pricing_stage=JobPricingStage.REALITY,
            )
            .annotate(local_date=F("accounting_date"))
            .values("local_date")
            .annotate(
                revenue=Sum(F("price_adjustment")), cost=Sum(F("cost_adjustment"))
            )
        )

        material_by_date = cls._process_entries(material_entries)

        adjustment_by_date = cls._process_entries(adjustment_entries)

        logger.debug(f"Retrieved data for {len(time_entries_by_date)} days")

        holiday_dates = cls._get_holidays(year, month)
        logger.debug(f"Holidays in {year}-{month}: {holiday_dates}")

        # For each day of the month
        current_date = start_date
        current_date_system = datetime.date.today()
        while current_date <= end_date:
            # Skip weekends (5=Saturday, 6=Sunday)
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            is_holiday = current_date in holiday_dates

            date_key = current_date.isoformat()
            base_data = {
                "date": date_key,
                "day": current_date.day,
                "holiday": is_holiday,
            }

            # Count all weekdays (including holidays) as working days
            monthly_totals["working_days"] += 1
            if current_date <= current_date_system:
                monthly_totals["elapsed_workdays"] += 1

            if is_holiday:
                base_data["holiday_name"] = holiday_dates[current_date]
                calendar_data[date_key] = base_data
                current_date += timedelta(days=1)
                continue

            logger.debug(f"Processing data for day: {current_date}")

            time_entry = time_entries_by_date.get(
                current_date,
                {
                    "total_hours": 0,
                    "billable_hours": 0,
                    "shop_hours": 0,
                    "time_revenue": 0,
                    "staff_cost": 0,
                    "material_revenue": 0,
                    "material_cost": 0,
                },
            )

            material_entry = material_by_date.get(
                current_date, {"revenue": 0, "cost": 0}
            )

            adjustment_entry = adjustment_by_date.get(
                current_date, {"revenue": 0, "cost": 0}
            )

            billable_hours = time_entry.get("billable_hours") or 0
            total_hours = time_entry.get("total_hours") or 0
            shop_hours = time_entry.get("shop_hours") or 0
            time_revenue = time_entry.get("time_revenue") or 0
            staff_cost = time_entry.get("staff_cost") or 0

            material_revenue = material_entry.get("revenue") or 0
            material_cost = material_entry.get("cost") or 0

            adjustment_revenue = adjustment_entry.get("revenue") or 0
            adjustment_cost = adjustment_entry.get("cost") or 0

            gross_profit = (time_revenue + material_revenue + adjustment_revenue) - (
                staff_cost + material_cost + adjustment_cost
            )
            shop_percentage = (
                (Decimal(shop_hours) / Decimal(total_hours) * 100)
                if total_hours > 0
                else Decimal("0")
            )

            # Increment status counters
            color = cls._get_color(
                billable_hours,
                thresholds["billable_threshold_green"],
                thresholds["billable_threshold_amber"],
            )

            match color:
                case "green":
                    monthly_totals["days_green"] += 1
                case "amber":
                    monthly_totals["days_amber"] += 1
                case _:
                    monthly_totals["days_red"] += 1

            # Only count performance for elapsed days (not future days)
            if current_date <= current_date_system:
                # Separate labour performance counting
                # (>=45h green, >=40h amber, <40h red)
                if billable_hours >= 45:
                    monthly_totals["labour_green_days"] += 1
                elif billable_hours >= 40:
                    monthly_totals["labour_amber_days"] += 1
                else:
                    monthly_totals["labour_red_days"] += 1

                # Separate profit performance counting
                # (>=$1250 green, >=$1000 amber, <$1000 red)
                if gross_profit >= 1250:
                    monthly_totals["profit_green_days"] += 1
                elif gross_profit >= 1000:
                    monthly_totals["profit_amber_days"] += 1
                else:
                    monthly_totals["profit_red_days"] += 1

            full_data = base_data.copy()
            full_data.update(
                {
                    "billable_hours": billable_hours,
                    "total_hours": total_hours,
                    "shop_hours": shop_hours,
                    "shop_percentage": float(shop_percentage),
                    "gross_profit": float(gross_profit),
                    "color": color,
                    "gp_target_achievement": float(
                        (
                            Decimal(gross_profit)
                            / Decimal(thresholds["daily_gp_target"])
                            * 100
                        )
                        if thresholds["daily_gp_target"] > 0
                        else 0
                    ),
                    "details": {
                        "time_revenue": float(time_revenue),
                        "material_revenue": float(material_revenue),
                        "adjustment_revenue": float(adjustment_revenue),
                        "total_revenue": float(
                            time_revenue + material_revenue + adjustment_revenue
                        ),
                        "staff_cost": float(staff_cost),
                        "material_cost": float(material_cost),
                        "adjustment_cost": float(adjustment_cost),
                        "total_cost": float(
                            staff_cost + material_cost + adjustment_cost
                        ),
                        "profit_breakdown": {
                            "labor_profit": float(time_revenue - staff_cost),
                            "material_profit": float(material_revenue - material_cost),
                            "adjustment_profit": float(
                                adjustment_revenue - adjustment_cost
                            ),
                        },
                        "job_breakdown": cls.get_job_breakdown_for_date(current_date),
                    },
                }
            )
            calendar_data[date_key] = full_data

            monthly_totals["billable_hours"] += billable_hours
            monthly_totals["total_hours"] += total_hours
            monthly_totals["shop_hours"] += shop_hours
            monthly_totals["gross_profit"] += gross_profit
            monthly_totals["material_revenue"] += material_revenue
            monthly_totals["adjustment_revenue"] += adjustment_revenue
            monthly_totals["time_revenue"] += time_revenue
            monthly_totals["staff_cost"] += staff_cost
            monthly_totals["material_cost"] += material_cost
            monthly_totals["adjustment_cost"] += adjustment_cost
            monthly_totals["material_profit"] += material_revenue - material_cost
            monthly_totals["adjustment_profit"] += adjustment_revenue - adjustment_cost

            # Advance to next day
            current_date += timedelta(days=1)

        monthly_totals["remaining_workdays"] = (
            monthly_totals["working_days"] - monthly_totals["elapsed_workdays"]
        )
        # Calculate percentages after all days processed
        cls._calculate_monthly_percentages(monthly_totals)

        billable_daily_avg = monthly_totals["avg_billable_hours_so_far"]
        monthly_totals["color_hours"] = cls._get_color(
            billable_daily_avg,
            thresholds["billable_threshold_green"],
            thresholds["billable_threshold_amber"],
        )

        gp_daily_avg = monthly_totals["avg_daily_gp_so_far"]
        monthly_totals["color_gp"] = cls._get_color(
            gp_daily_avg,
            thresholds["daily_gp_target"],
            (thresholds["daily_gp_target"] / 2),
        )

        shop_percentage = monthly_totals["shop_percentage"]
        monthly_totals["color_shop"] = cls._get_color(
            20.0,  # Target threshold (reverse logic - lower is better)
            shop_percentage,
            25.0,  # Warning threshold
        )

        logger.info(
            f"Monthly totals: billable: {monthly_totals['billable_hours']:.1f}h, "
            f"billable %: {monthly_totals['billable_percentage']:.1f}%"
        )
        logger.info(
            f"Performance: green days: {monthly_totals['days_green']}, "
            f"amber: {monthly_totals['days_amber']}, red: {monthly_totals['days_red']}"
        )
        response_data = {
            "calendar_data": calendar_data,
            "monthly_totals": monthly_totals,
            "thresholds": thresholds,
            "year": year,
            "month": month,
        }
        logger.debug(f"Calendar data generated with {len(calendar_data)} days")
        return response_data

    @staticmethod
    def _calculate_monthly_percentages(monthly_totals: Dict[str, float]) -> None:
        """
        Calculate percentages and medias for monthly totals

        Args:
            monthly_totals: Dict of monthly totals to be updated
        """
        logger.debug("Calculating monthly percentages")

        # Initialize default values
        monthly_totals["billable_percentage"] = 0
        monthly_totals["shop_percentage"] = 0
        monthly_totals["avg_daily_gp"] = 0
        monthly_totals["avg_daily_gp_so_far"] = 0
        monthly_totals["avg_billable_hours_so_far"] = 0

        # Calculate billable and shop percentages if we have hours
        if monthly_totals["total_hours"] > 0:
            monthly_totals["billable_percentage"] = round(
                Decimal(monthly_totals["billable_hours"])
                / Decimal(monthly_totals["total_hours"])
                * 100,
                1,
            )
            monthly_totals["shop_percentage"] = round(
                Decimal(monthly_totals["shop_hours"] / monthly_totals["total_hours"])
                * 100,
                1,
            )
            logger.debug(
                f"Calculated billable %: {monthly_totals['billable_percentage']}%, "
                f"shop percentage: {monthly_totals['shop_percentage']}%"
            )

        # Calculate average daily gross profit if we have working days
        if monthly_totals["working_days"] > 0:
            monthly_totals["avg_daily_gp"] = round(
                Decimal(
                    monthly_totals["gross_profit"] / monthly_totals["working_days"]
                ),
                2,
            )
            logger.debug(
                f"Calculated average daily gross profit: "
                f"${monthly_totals['avg_daily_gp']}"
            )
        else:
            logger.warning("No working days found for month - average GP will be zero")

        # Calculate average daily gross profit and billable hours so far
        # based on elapsed days
        if monthly_totals["elapsed_workdays"] > 0:
            monthly_totals["avg_daily_gp_so_far"] = round(
                Decimal(monthly_totals["gross_profit"])
                / Decimal(monthly_totals["elapsed_workdays"]),
                2,
            )
            monthly_totals["avg_billable_hours_so_far"] = round(
                Decimal(monthly_totals["billable_hours"])
                / Decimal(monthly_totals["elapsed_workdays"]),
                1,
            )
