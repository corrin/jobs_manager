"""
Django shell script for testing MCP Quoting Tools
Run with: python manage.py shell < test_mcp_shell.py
"""

import logging

from apps.client.models import Supplier
from apps.job.models import Job
from apps.quoting.mcp import QuotingTool, SupplierProductQueryTool
from apps.quoting.models import ScrapeJob, SupplierPriceList, SupplierProduct

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Initialize the tools
quoting_tool = QuotingTool()
query_tool = SupplierProductQueryTool()

logger.info("🔧 MCP Quoting Tools - Interactive Test Session")
logger.info("=" * 50)

# Data summary
logger.info("\n📊 Current Data Summary:")
logger.info(f"Suppliers: {Supplier.objects.count()}")
logger.info(f"Jobs: {Job.objects.count()}")
logger.info(f"Supplier Products: {SupplierProduct.objects.count()}")
logger.info(f"Price Lists: {SupplierPriceList.objects.count()}")
logger.info(f"Scrape Jobs: {ScrapeJob.objects.count()}")

# Available test commands
logger.info("\n🧪 Available Test Commands:")
logger.info("1. quoting_tool.search_products('steel')")
logger.info("2. quoting_tool.get_pricing_for_material('aluminum', '4x8')")
logger.info("3. quoting_tool.get_supplier_status()")
logger.info("4. quoting_tool.compare_suppliers('steel')")
logger.info("5. query_tool.get_queryset().count()")

# Sample job for quote testing
sample_job = Job.objects.first()
if sample_job:
    logger.info(
        f"6. quoting_tool.create_quote_estimate('{sample_job.id}', 'steel sheet', 8.0)"
    )

logger.info("\n" + "=" * 50)
logger.info("Ready for testing! Try the commands above.")
