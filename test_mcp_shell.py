"""
Django shell script for testing MCP Quoting Tools
Run with: python manage.py shell < test_mcp_shell.py
"""

from apps.client.models import Client, Supplier
from apps.job.models import Job
from apps.quoting.mcp import QuotingTool, SupplierProductQueryTool
from apps.quoting.models import ScrapeJob, SupplierPriceList, SupplierProduct

# Initialize the tools
quoting_tool = QuotingTool()
query_tool = SupplierProductQueryTool()

print("🔧 MCP Quoting Tools - Interactive Test Session")
print("=" * 50)

# Data summary
print("\n📊 Current Data Summary:")
print(f"Suppliers: {Supplier.objects.count()}")
print(f"Jobs: {Job.objects.count()}")
print(f"Supplier Products: {SupplierProduct.objects.count()}")
print(f"Price Lists: {SupplierPriceList.objects.count()}")
print(f"Scrape Jobs: {ScrapeJob.objects.count()}")

# Available test commands
print("\n🧪 Available Test Commands:")
print("1. quoting_tool.search_products('steel')")
print("2. quoting_tool.get_pricing_for_material('aluminum', '4x8')")
print("3. quoting_tool.get_supplier_status()")
print("4. quoting_tool.compare_suppliers('steel')")
print("5. query_tool.get_queryset().count()")

# Sample job for quote testing
sample_job = Job.objects.first()
if sample_job:
    print(
        f"6. quoting_tool.create_quote_estimate('{sample_job.id}', 'steel sheet', 8.0)"
    )

print("\n" + "=" * 50)
print("Ready for testing! Try the commands above.")
