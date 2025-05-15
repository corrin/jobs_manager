import datetime

import calendar

import holidays

from decimal import Decimal

from typing import Dict, Any, Tuple

from datetime import date, timedelta

from django.db.models import Sum, Case, When, F, DecimalField, Value

from django.db.models.functions import TruncDate

from django.utils import timezone

from logging import getLogger

from workflow.models import CompanyDefaults
from workflow.models.adjustment_entry import AdjustmentEntry
from workflow.models.material_entry import MaterialEntry
from workflow.utils import get_nz_tz

from accounts.utils import get_excluded_staff

from timesheet.models import TimeEntry

logger = getLogger(__name__)


class KPIService:
    """
    Service responsible for calculating and providing KPI metrics for reports.
    All business logic related to KPIs shall be implemented here.
    """

    nz_timezone = get_nz_tz()

    shop_job_id: str = "00000000-0000-0000-0000-000000000001"


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
                "billable_threshold_green": float(company_defaults.billable_threshold_green),
                "billable_threshold_amber": float(company_defaults.billable_threshold_amber),
                "daily_gp_target": float(company_defaults.daily_gp_target),
                "shop_hours_target": float(company_defaults.shop_hours_target_percentage)
            }
            logger.debug(f"Retrieved thresholds: {thresholds}")
            return thresholds
        except Exception as e:
            logger.error(f"Error retrieving company defaults: {str(e)}")
            raise
    
    @staticmethod
    def _process_entries(entries: Dict, revenue_key="revenue", cost_key="cost") -> Dict[datetime.date, Dict]:
        """
        Segregates entries by date based on the provided Dict
        """
        entries_by_date = {
            entry["local_date"]: {
                "revenue": entry.get(revenue_key) or 0,
                "cost":    entry.get(cost_key) or 0
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
        nz_holidays = holidays.country_holidays('NZ', years=year)

        if month:
            return {date: name for date, name in nz_holidays.items() if date.month == month}
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
        
        logger.debug(f"Date range: {start_date} to {end_date}, days in month: {num_days}")
        return start_date, end_date, num_days
    
    @staticmethod
    def _get_color(value: float | Decimal, green_threshold: float, amber_threshold: float) -> str:
        if value >= green_threshold:
            return "green"
        if value >= amber_threshold:
            return "amber"
        return "red"

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
        
        thresholds = cls.get_company_thresholds()
        logger.debug(f"Using thresholds: green={thresholds['billable_threshold_green']}, amber={thresholds['billable_threshold_amber']}")

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
            "working_days": 0,
            "elapsed_workdays": 0,
            "remaining_workdays": 0,
            # The following are internal
            "time_revenue": 0,
            "material_revenue": 0,
            "staff_cost": 0,
            "material_cost": 0,
        }

        decimal_field = DecimalField(max_digits=10, decimal_places=2)
        # Process data of the day
        time_entries_by_date = { 
            entry["date"]: entry for entry in TimeEntry.objects.filter(
                date__range=[start_date, end_date]
            ).exclude(
                staff_id__in=excluded_staff_ids
            ).values("date").annotate(
                total_hours=Sum(
                    "hours", 
                    output_field=decimal_field
                ),
                billable_hours=Sum(
                    Case(
                        When(is_billable=True, then="hours"), 
                        default=Value(0, output_field=decimal_field)
                    ),
                    output_field=decimal_field
                ),
                time_revenue=Sum(
                    Case(
                        When(is_billable=True, then=F("hours") * F("charge_out_rate")), 
                        default=Value(0, output_field=decimal_field)
                    ), 
                    output_field=decimal_field
                ),
                shop_hours=Sum(
                    Case(
                        When(job_pricing__job__client_id=cls.shop_job_id, then="hours"), 
                        default=Value(0, output_field=decimal_field)
                    ), 
                    output_field=decimal_field
                ),
                staff_cost=Sum(
                    F("hours") * F("wage_rate"), 
                    output_field=decimal_field
                )
            )
        }

        aware_start = timezone.make_aware(
            datetime.datetime.combine(start_date, datetime.time.min),
            cls.nz_timezone
        )
        aware_end = timezone.make_aware(
            datetime.datetime.combine(end_date, datetime.time.max),
            cls.nz_timezone
        )

        material_entries = MaterialEntry.objects.filter(
            created_at__range=[aware_start, aware_end]
        ).annotate(
            local_date=TruncDate('created_at', tzinfo=cls.nz_timezone)
        ).values("local_date").annotate(
            revenue=Sum(F("unit_revenue") * F("quantity"), output_field=decimal_field),
            cost=Sum(F("unit_cost") * F("quantity"), output_field=decimal_field)
        )

        adjustment_entries = AdjustmentEntry.objects.filter(
            created_at__range=[aware_start, aware_end]
        ).annotate(
            local_date=TruncDate('created_at', tzinfo=cls.nz_timezone)
        ).values("local_date").annotate(
            revenue=Sum(F("price_adjustment")),
            cost=Sum(F("cost_adjustment"))
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
                "holiday": is_holiday
            }

            if is_holiday:
                base_data["holiday_name"] = holiday_dates[current_date]
                calendar_data[date_key] = base_data
                current_date += timedelta(days=1)
                continue

            # Count commercial day
            monthly_totals["working_days"] += 1
            if current_date <= current_date_system:
                monthly_totals["elapsed_workdays"] += 1

            logger.debug(f"Processing data for day: {current_date}")

            time_entry = time_entries_by_date.get(current_date, {
                "total_hours": 0,
                "billable_hours": 0,
                "shop_hours": 0,
                "time_revenue": 0,
                "staff_cost": 0,
                "material_revenue": 0,
                "material_cost": 0
            })

            material_entry = material_by_date.get(current_date, {
                "revenue": 0,
                "cost": 0
            })

            adjustment_entry = adjustment_by_date.get(current_date, {
                "revenue": 0,
                "cost": 0
            })

            billable_hours = time_entry.get("billable_hours") or 0
            total_hours = time_entry.get("total_hours") or 0
            shop_hours = time_entry.get("shop_hours") or 0
            time_revenue = time_entry.get("time_revenue") or 0
            staff_cost = time_entry.get("staff_cost") or 0

            material_revenue = material_entry.get("revenue") or 0
            material_cost = material_entry.get("cost") or 0

            adjustment_revenue = adjustment_entry.get("revenue") or 0
            adjustment_cost = adjustment_entry.get("cost") or 0

            gross_profit = (time_revenue + material_revenue + adjustment_revenue) - (staff_cost + material_cost + adjustment_cost)
            shop_percentage = (Decimal(shop_hours) / Decimal(total_hours) * 100) if total_hours > 0 else Decimal("0")

            # Increment status counters
            color = cls._get_color(
                billable_hours,
                thresholds["billable_threshold_green"],
                thresholds["billable_threshold_amber"]
            )

            match color:
                case "green":
                    monthly_totals["days_green"] += 1
                case "amber":
                    monthly_totals["days_amber"] += 1
                case _:
                    monthly_totals["days_red"] += 1

            full_data = base_data.copy()
            full_data.update({
                "billable_hours": billable_hours,
                "total_hours": total_hours,
                "shop_hours": shop_hours,
                "shop_percentage": float(shop_percentage),
                "gross_profit": float(gross_profit),
                "color": color,
                "gp_target_achievement": float((Decimal(gross_profit) / Decimal(thresholds["daily_gp_target"]) * 100) if thresholds["daily_gp_target"] > 0 else 0),
                "details": {
                    "time_revenue": float(time_revenue),
                    "material_revenue": float(material_revenue),
                    "adjustment_revenue": float(adjustment_revenue),
                    "total_revenue": float(time_revenue + material_revenue + adjustment_revenue),
                    "staff_cost": float(staff_cost),
                    "material_cost": float(material_cost),
                    "adjustment_cost": float(adjustment_cost),
                    "total_cost": float(staff_cost + material_cost + adjustment_cost),
                    "profit_breakdown": {
                        "labor_profit": float(time_revenue - staff_cost),
                        "material_profit": float(material_revenue - material_cost),
                        "adjustment_profit": float(adjustment_revenue - adjustment_cost)
                    }
                }
            })
            calendar_data[date_key] = full_data

            monthly_totals["billable_hours"] += billable_hours
            monthly_totals["total_hours"] += total_hours
            monthly_totals["shop_hours"] += shop_hours
            monthly_totals["gross_profit"] += gross_profit
            monthly_totals["material_revenue"] += material_revenue
            monthly_totals["time_revenue"] += time_revenue
            monthly_totals["staff_cost"] += staff_cost
            monthly_totals["material_cost"] += material_cost

            # Advance to next day
            current_date += timedelta(days=1)

        monthly_totals["remaining_workdays"] = monthly_totals["working_days"] - monthly_totals["elapsed_workdays"]
        # Calculate percentages after all days processed
        cls._calculate_monthly_percentages(monthly_totals)

        billable_daily_avg = monthly_totals["avg_billable_hours_so_far"]
        monthly_totals["color_hours"] = cls._get_color(
            billable_daily_avg,
            thresholds["billable_threshold_green"],
            thresholds["billable_threshold_amber"]
        )
        
        gp_daily_avg = monthly_totals["avg_daily_gp_so_far"]
        monthly_totals["color_gp"] = cls._get_color(
            gp_daily_avg,
            thresholds["daily_gp_target"],
            (thresholds["daily_gp_target"] / 2)
        )
        
        shop_percentage = monthly_totals["shop_percentage"]
        monthly_totals["color_shop"] = cls._get_color(
            20.0,  # Target threshold (reverse logic - lower is better)
            shop_percentage,
            25.0   # Warning threshold
        )
        
        logger.info(f"Monthly totals: billable: {monthly_totals['billable_hours']:.1f}h, billable %: {monthly_totals['billable_percentage']:.1f}%")
        logger.info(f"Performance: green days: {monthly_totals['days_green']}, amber: {monthly_totals['days_amber']}, red: {monthly_totals['days_red']}")
        response_data = {
            "calendar_data": calendar_data,
            "monthly_totals": monthly_totals,
            "thresholds": thresholds,
            "year": year,
            "month": month
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
                Decimal(monthly_totals["billable_hours"]) / Decimal(monthly_totals["total_hours"])  * 100, 1
            )
            monthly_totals["shop_percentage"] = round(
                Decimal(monthly_totals["shop_hours"] / monthly_totals["total_hours"]) * 100, 1
            )
            logger.debug(f"Calculated billable percentage: {monthly_totals['billable_percentage']}%, shop percentage: {monthly_totals['shop_percentage']}%")

        # Calculate average daily gross profit if we have working days
        if monthly_totals["working_days"] > 0:
            monthly_totals["avg_daily_gp"] = round(
                Decimal(monthly_totals["gross_profit"] / monthly_totals["working_days"]), 2
            )
            logger.debug(f"Calculated average daily gross profit: ${monthly_totals['avg_daily_gp']}")
        else:
            logger.warning("No working days found for month - average GP will be zero")
        
        # Calculate average daily gross profit and billable hours so far based on elapsed days
        if monthly_totals["elapsed_workdays"] > 0:
            monthly_totals["avg_daily_gp_so_far"] = round(
                Decimal(monthly_totals["gross_profit"]) / Decimal(monthly_totals["elapsed_workdays"]), 2
            )
            monthly_totals["avg_billable_hours_so_far"] = round(
                Decimal(monthly_totals["billable_hours"]) / Decimal(monthly_totals["elapsed_workdays"]), 1
            )
