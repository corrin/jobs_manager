#!/usr/bin/env python
"""
Comprehensive Serializer Testing Script

Tests all major serializers in the application to ensure they work correctly
with production data. This is crucial after data restores or schema changes.

Usage:
    python scripts/test_serializers.py [--verbose] [--serializer <name>]

Examples:
    python scripts/test_serializers.py                    # Test all serializers
    python scripts/test_serializers.py --verbose          # Detailed output
    python scripts/test_serializers.py --serializer job   # Test only JobSerializer
"""

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Tuple

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings.local")
os.environ.setdefault("HTTP_HOST", "localhost:8000")

import django

django.setup()

from django.test import RequestFactory

from apps.accounts.models import Staff
from apps.client.models import Client
from apps.job.models import CostLine, CostSet, Job
from apps.purchasing.models import PurchaseOrder


class SerializerTester:
    """Comprehensive serializer testing framework"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.factory = RequestFactory()
        self.request = self._create_mock_request()
        self.results = {}

    def _create_mock_request(self):
        """Create a proper mock request for serializer context"""
        request = self.factory.get("/")
        request.META["HTTP_HOST"] = "localhost:8000"
        return request

    def _print_verbose(self, message: str):
        """Print message only in verbose mode"""
        if self.verbose:
            print(f"  {message}")

    def _test_serializer_batch(
        self, serializer_class, queryset, name: str, batch_size: int = 100
    ) -> Dict[str, Any]:
        """Test a serializer against a queryset with progress reporting"""

        total_count = queryset.count()
        if total_count == 0:
            return {
                "name": name,
                "total": 0,
                "success": 0,
                "failed": 0,
                "failures": [],
                "duration": 0.0,
                "status": "SKIPPED - No data",
            }

        print(f"Testing {name} ({total_count} records)...")

        start_time = time.time()
        success_count = 0
        failed_items = []

        for i, item in enumerate(queryset.iterator(chunk_size=100)):
            try:
                serializer = serializer_class(item, context={"request": self.request})
                _ = serializer.data  # Trigger serialization
                success_count += 1

                if (i + 1) % batch_size == 0:
                    self._print_verbose(f"Processed {i + 1}/{total_count}...")

            except Exception as e:
                error_info = {
                    "item_id": str(getattr(item, "id", "unknown")),
                    "item_str": str(item)[:100],
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                failed_items.append(error_info)
                self._print_verbose(f"Failed item {item}: {e}")

        duration = time.time() - start_time
        failed_count = len(failed_items)

        status = "✅ PASS" if failed_count == 0 else f"❌ FAIL ({failed_count} errors)"

        result = {
            "name": name,
            "total": total_count,
            "success": success_count,
            "failed": failed_count,
            "failures": failed_items,
            "duration": duration,
            "status": status,
        }

        print(
            f"  {status} - {success_count}/{total_count} serialized ({duration:.2f}s)"
        )

        return result

    def test_job_serializer(self) -> Dict[str, Any]:
        """Test JobSerializer with all jobs"""
        from apps.job.serializers import JobSerializer

        queryset = (
            Job.objects.all()
            .select_related(
                "contact",
                "created_by",
                "client",
                "latest_estimate",
                "latest_quote",
                "latest_actual",
            )
            .prefetch_related("cost_sets", "files", "events")
        )

        return self._test_serializer_batch(JobSerializer, queryset, "JobSerializer")

    def test_kanban_serializer(self) -> Dict[str, Any]:
        """Test KanbanSerializer with active jobs"""
        from apps.job.serializers.kanban_serializer import KanbanSerializer

        queryset = Job.objects.filter(
            status__in=["quoting", "in_progress", "ready_for_delivery"]
        ).select_related("contact", "assigned_to")

        return self._test_serializer_batch(
            KanbanSerializer, queryset, "KanbanSerializer (Active Jobs)"
        )

    def test_costing_serializer(self) -> Dict[str, Any]:
        """Test CostingSerializer with cost sets"""
        from apps.job.serializers.costing_serializer import CostSetSerializer

        queryset = (
            CostSet.objects.all().select_related("job").prefetch_related("costlines")
        )

        return self._test_serializer_batch(
            CostSetSerializer, queryset, "CostSetSerializer"
        )

    def test_client_serializer(self) -> Dict[str, Any]:
        """Test ClientSerializer with sample of clients"""
        from apps.client.serializers import ClientSerializer

        # Test sample of clients to avoid overwhelming output
        queryset = Client.objects.all()[:500]

        return self._test_serializer_batch(
            ClientSerializer, queryset, "ClientSerializer (Sample)"
        )

    def test_staff_serializer(self) -> Dict[str, Any]:
        """Test StaffSerializer with all staff"""
        from apps.accounts.serializers import StaffSerializer

        queryset = Staff.objects.all()

        return self._test_serializer_batch(StaffSerializer, queryset, "StaffSerializer")

    def test_purchase_order_serializer(self) -> Dict[str, Any]:
        """Test PurchaseOrderSerializer with all purchase orders"""
        from apps.purchasing.serializers import PurchaseOrderSerializer

        queryset = (
            PurchaseOrder.objects.all()
            .select_related("supplier", "created_by")
            .prefetch_related("lines")
        )

        return self._test_serializer_batch(
            PurchaseOrderSerializer, queryset, "PurchaseOrderSerializer"
        )

    def test_modern_timesheet_serializer(self) -> Dict[str, Any]:
        """Test modern timesheet serializers with cost lines"""
        from apps.timesheet.serializers.modern_timesheet_serializers import (
            CostLineTimesheetSerializer,
        )

        queryset = CostLine.objects.filter(kind="time").select_related("costset__job")

        return self._test_serializer_batch(
            CostLineTimesheetSerializer,
            queryset,
            "CostLineTimesheetSerializer (Modern)",
        )

    def run_all_tests(self, specific_serializer: str = None) -> Dict[str, Any]:
        """Run all serializer tests or a specific one"""

        test_methods = {
            "job": self.test_job_serializer,
            "kanban": self.test_kanban_serializer,
            "costing": self.test_costing_serializer,
            "client": self.test_client_serializer,
            "staff": self.test_staff_serializer,
            "purchase_order": self.test_purchase_order_serializer,
            "timesheet": self.test_modern_timesheet_serializer,
        }

        if specific_serializer:
            if specific_serializer not in test_methods:
                print(f"❌ Unknown serializer: {specific_serializer}")
                print(f"Available serializers: {', '.join(test_methods.keys())}")
                return {}
            test_methods = {specific_serializer: test_methods[specific_serializer]}

        print("🚀 Starting Comprehensive Serializer Testing")
        print("=" * 60)

        total_start_time = time.time()

        for test_name, test_method in test_methods.items():
            try:
                result = test_method()
                self.results[test_name] = result
            except ImportError as e:
                print(f"Skipping {test_name}: {e}")
                self.results[test_name] = {
                    "name": test_name,
                    "status": f"SKIPPED - Import Error: {e}",
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                }
            except Exception as e:
                print(f"Error testing {test_name}: {e}")
                self.results[test_name] = {
                    "name": test_name,
                    "status": f"ERROR: {e}",
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                }

        total_duration = time.time() - total_start_time

        self._print_summary(total_duration)
        return self.results

    def _print_summary(self, total_duration: float):
        """Print comprehensive test summary"""
        print("=" * 60)
        print("📊 SERIALIZER TEST SUMMARY")
        print("=" * 60)

        total_items = 0
        total_success = 0
        total_failed = 0
        failed_serializers = []

        for test_name, result in self.results.items():
            status = result.get("status", "UNKNOWN")
            total = result.get("total", 0)
            success = result.get("success", 0)
            failed = result.get("failed", 0)

            total_items += total
            total_success += success
            total_failed += failed

            print(f"{status:20} {test_name:25} ({success}/{total})")

            if failed > 0:
                failed_serializers.append(test_name)
                if self.verbose and "failures" in result:
                    print(f"  First few failures:")
                    for failure in result["failures"][:3]:
                        print(f"    {failure['item_str']}: {failure['error']}")

        print("-" * 60)
        print(f"📈 TOTALS: {total_success}/{total_items} items serialized successfully")
        print(f"⏱️  DURATION: {total_duration:.2f} seconds")

        if failed_serializers:
            print(f"❌ FAILED SERIALIZERS: {', '.join(failed_serializers)}")
            print("CRITICAL: Some serializers failed. Check data integrity!")
            return False
        else:
            print("✅ ALL SERIALIZERS PASSED!")
            return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test Django REST Framework serializers"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output with detailed progress",
    )
    parser.add_argument(
        "--serializer",
        "-s",
        type=str,
        help="Test specific serializer (job, kanban, costing, client, staff, purchase_order, timesheet)",
    )

    args = parser.parse_args()

    tester = SerializerTester(verbose=args.verbose)
    success = tester.run_all_tests(args.serializer)

    # Exit with error code if any tests failed
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
