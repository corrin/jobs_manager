# quoting/management/commands/run_scrapers.py
import importlib
import inspect
import logging
import os

from django.core.management.base import BaseCommand

from apps.client.models import Supplier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run product scrapers for suppliers"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scraper",
            type=str,
            help='Specific scraper class name to run (e.g., "SteelAndTubeScraper")',
        )
        parser.add_argument(
            "--supplier",
            type=str,
            help='Specific supplier name to scrape (e.g., "Steel & Tube")',
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of URLs to process (for testing)",
        )
        parser.add_argument(
            "--force", action="store_true", help="Force re-scrape of existing products"
        )

    def handle(self, *args, **options):
        scraper_name = options.get("scraper")
        supplier_name = options.get("supplier")
        limit = options.get("limit")
        force = options.get("force")

        logger.info("Starting scraper runner...")

        # Get available scrapers
        available_scrapers = self.get_available_scrapers()
        if not available_scrapers:
            logger.error("No scrapers found in quoting/scrapers directory")
            return

        logger.info(
            f"Found {len(available_scrapers)} available scrapers: {[s['class_name'] for s in available_scrapers]}"
        )

        # Filter scrapers to run
        if scraper_name:
            scrapers_to_run = [
                s for s in available_scrapers if s["class_name"] == scraper_name
            ]
            if not scrapers_to_run:
                logger.error(
                    f"Scraper '{scraper_name}' not found. Available: {[s['class_name'] for s in available_scrapers]}"
                )
                return
        else:
            scrapers_to_run = available_scrapers

        logger.info(f"Will run {len(scrapers_to_run)} scrapers")

        # Run each scraper
        for scraper_info in scrapers_to_run:
            try:
                self.run_scraper(scraper_info, supplier_name, limit, force)
            except Exception as e:
                logger.error(f"Error running scraper {scraper_info['class_name']}: {e}")
                continue

        logger.info("Scraper runner completed")

    def get_available_scrapers(self):
        """Discover all scraper classes in the scrapers directory"""
        scrapers = []
        scrapers_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scrapers")

        if not os.path.exists(scrapers_dir):
            logger.error(f"Scrapers directory not found: {scrapers_dir}")
            return []

        for filename in os.listdir(scrapers_dir):
            if (
                filename.endswith(".py")
                and not filename.startswith("__")
                and filename != "base.py"
            ):
                module_name = filename[:-3]  # Remove .py extension

                try:
                    # Import the module
                    module = importlib.import_module(
                        f"apps.quoting.scrapers.{module_name}"
                    )

                    # Look for classes that end with 'Scraper' (except BaseScraper)
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if name.endswith("Scraper") and name != "BaseScraper":
                            scrapers.append(
                                {
                                    "class_name": name,
                                    "module_name": module_name,
                                    "class_obj": obj,
                                    "docstring": obj.__doc__
                                    or f"Scraper for {name.replace('Scraper', '')}",
                                }
                            )

                except ImportError as e:
                    logger.warning(
                        f"Could not import scraper module {module_name}: {e}"
                    )
                    continue
                except Exception as e:
                    logger.warning(
                        f"Error processing scraper module {module_name}: {e}"
                    )
                    continue

        return scrapers

    def run_scraper(self, scraper_info, supplier_name, limit, force):
        """Run a specific scraper"""
        scraper_class = scraper_info["class_obj"]
        class_name = scraper_info["class_name"]

        logger.info(f"Starting scraper: {class_name}")

        # Find the supplier for this scraper
        supplier = self.find_supplier_for_scraper(class_name, supplier_name)
        if not supplier:
            logger.error(f"No suitable supplier found for scraper {class_name}")
            return

        logger.info(f"Running {class_name} for supplier: {supplier.name}")

        try:
            # Create and run the scraper
            scraper = scraper_class(supplier, limit=limit, force=force)
            scraper.run()
            logger.info(f"Completed scraper: {class_name}")

        except Exception as e:
            logger.error(f"Error running scraper {class_name}: {e}")
            raise

    def find_supplier_for_scraper(self, scraper_class_name, supplier_name_filter=None):
        """Find the supplier that should use this scraper"""

        # If specific supplier name provided, find it
        if supplier_name_filter:
            try:
                supplier = Supplier.objects.get(name__icontains=supplier_name_filter)
                return supplier
            except Supplier.DoesNotExist:
                logger.error(f"Supplier matching '{supplier_name_filter}' not found")
                return None
            except Supplier.MultipleObjectsReturned:
                logger.error(
                    f"Multiple suppliers found matching '{supplier_name_filter}' - be more specific"
                )
                return None

        # Hardcoded supplier mappings
        if scraper_class_name == "SteelAndTubeScraper":
            try:
                supplier = Supplier.objects.get(
                    xero_contact_id="92bd100c-b0e5-45e7-84d9-1ed883050353"
                )
                logger.info(f"Found supplier by hardcoded Xero ID: {supplier.name}")
                return supplier
            except Supplier.DoesNotExist:
                logger.error(
                    "S&T Stainless Limited supplier not found with Xero ID 92bd100c-b0e5-45e7-84d9-1ed883050353"
                )
                return None

        # Otherwise, try to match by scraper name to supplier name
        # SteelAndTubeScraper -> Steel & Tube
        scraper_supplier_name = scraper_class_name.replace("Scraper", "").replace(
            "And", " & "
        )
        try:
            supplier = Supplier.objects.get(name__icontains=scraper_supplier_name)
            logger.info(f"Found supplier by name matching: {supplier.name}")
            return supplier
        except Supplier.DoesNotExist:
            logger.error(
                f"No supplier found matching scraper name pattern '{scraper_supplier_name}'"
            )
            return None
        except Supplier.MultipleObjectsReturned:
            suppliers = Supplier.objects.filter(name__icontains=scraper_supplier_name)
            logger.error(
                f"Multiple suppliers found for pattern '{scraper_supplier_name}': {[s.name for s in suppliers]}"
            )
            return None


# Usage examples:
# python manage.py run_scrapers                                    # Run all scrapers
# python manage.py run_scrapers --scraper SteelAndTubeScraper      # Run specific scraper
# python manage.py run_scrapers --supplier "Steel & Tube"          # Run scraper for specific supplier
# python manage.py run_scrapers --limit 10 --force                 # Run all with options
# python manage.py run_scrapers --scraper SteelAndTubeScraper --limit 5
