import logging
import time
from typing import Set

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.quoting.models import ProductParsingMapping, SupplierProduct
from apps.quoting.services.product_parser import ProductParser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Populate ProductParsingMapping from existing SupplierProduct records with rate limiting"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Number of products to process per batch (default: 50)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=2.0,
            help="Delay in seconds between API calls (default: 5.0)",
        )
        parser.add_argument(
            "--max-products",
            type=int,
            help="Maximum number of products to process (for testing)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without making API calls",
        )
        parser.add_argument(
            "--resume", action="store_true", help="Resume from where last run left off"
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        delay = options["delay"]
        max_products = options["max_products"]
        dry_run = options["dry_run"]
        options["resume"]

        self.stdout.write(
            self.style.SUCCESS("Starting ProductParsingMapping population")
        )
        self.stdout.write(f"Batch size: {batch_size}")
        self.stdout.write(f"Delay between batches: {delay}s")
        if max_products:
            self.stdout.write(f"Max products to process: {max_products}")
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No API calls will be made")
            )

        try:
            # Get current state
            total_supplier_products = SupplierProduct.objects.count()
            existing_mappings = ProductParsingMapping.objects.count()

            self.stdout.write(
                f"Total SupplierProduct records: {total_supplier_products}"
            )
            self.stdout.write(
                f"Existing ProductParsingMapping records: {existing_mappings}"
            )

            # Find unprocessed products
            processed_hashes = self._get_processed_hashes()
            unprocessed_products = self._get_unprocessed_products(processed_hashes)

            if max_products:
                unprocessed_products = unprocessed_products[:max_products]

            total_to_process = len(unprocessed_products)
            self.stdout.write(f"Products needing processing: {total_to_process}")

            if total_to_process == 0:
                self.stdout.write(self.style.SUCCESS("All products already processed!"))
                return

            if dry_run:
                self.stdout.write("Dry run complete. Products that would be processed:")
                for i, product in enumerate(unprocessed_products[:10]):  # Show first 10
                    self.stdout.write(f"  {i + 1}. {product.product_name[:50]}...")
                if total_to_process > 10:
                    self.stdout.write(f"  ... and {total_to_process - 10} more")
                return

            # Initialize parser
            parser = ProductParser()

            # Process in batches
            processed_count = 0
            failed_count = 0
            start_time = timezone.now()

            for i in range(0, total_to_process, batch_size):
                batch = unprocessed_products[i : i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_to_process + batch_size - 1) // batch_size

                self.stdout.write(
                    f"Processing batch {batch_num}/{total_batches} "
                    f"({len(batch)} products)..."
                )

                # Prepare batch data
                product_data_list = []
                for product in batch:
                    product_data_list.append(
                        {
                            "description": product.description,
                            "product_name": product.product_name,
                            "specifications": product.specifications,
                            "item_no": product.item_no,
                            "variant_id": product.variant_id,
                            "variant_width": product.variant_width,
                            "variant_length": product.variant_length,
                            "variant_price": product.variant_price,
                            "price_unit": product.price_unit,
                            "supplier_name": product.supplier.name,
                        }
                    )

                # Process batch with error handling
                try:
                    with transaction.atomic():
                        results = parser.parse_products_batch(product_data_list)

                        # Count successful results
                        successful_results = [r for r in results if r and len(r) == 2]
                        processed_count += len(successful_results)
                        failed_count += len(batch) - len(successful_results)

                        self.stdout.write(
                            f"  ✓ Batch {batch_num} complete: {len(successful_results)}/{len(batch)} successful"
                        )

                except Exception as e:
                    failed_count += len(batch)
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Batch {batch_num} failed: {e}")
                    )
                    logger.error(f"Batch processing failed: {e}")

                # Progress update
                total_processed_so_far = processed_count + failed_count
                progress_pct = (total_processed_so_far / total_to_process) * 100
                elapsed = timezone.now() - start_time

                if total_processed_so_far > 0:
                    estimated_total_time = elapsed * (
                        total_to_process / total_processed_so_far
                    )
                    remaining_time = estimated_total_time - elapsed

                    self.stdout.write(
                        f"Progress: {total_processed_so_far}/{total_to_process} "
                        f"({progress_pct:.1f}%) - "
                        f"ETA: {remaining_time}"
                    )

                # Rate limiting delay (except for last batch)
                if i + batch_size < total_to_process:
                    self.stdout.write(f"  Waiting {delay}s before next batch...")
                    time.sleep(delay)

            # Final statistics
            self.stdout.write(self.style.SUCCESS("\n=== FINAL RESULTS ==="))
            self.stdout.write(f"Total products processed: {processed_count}")
            self.stdout.write(f"Total products failed: {failed_count}")
            self.stdout.write(
                f"Success rate: {(processed_count / total_to_process * 100):.1f}%"
            )
            self.stdout.write(f"Total time: {timezone.now() - start_time}")

            # Updated counts
            new_mapping_count = ProductParsingMapping.objects.count()
            self.stdout.write(
                f"ProductParsingMapping records: {existing_mappings} → {new_mapping_count}"
            )

            if failed_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n{failed_count} products failed to process. "
                        "You can re-run this command with --resume to retry failed items."
                    )
                )

        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise CommandError(f"Failed to populate mappings: {e}")

    def _get_processed_hashes(self) -> Set[str]:
        """Get set of input hashes that have already been processed."""
        return set(ProductParsingMapping.objects.values_list("input_hash", flat=True))

    def _get_unprocessed_products(self, processed_hashes: Set[str]) -> list:
        """Get list of SupplierProduct records that haven't been processed yet."""
        parser = ProductParser()
        unprocessed = []

        self.stdout.write("Checking which products need processing...")

        # Get all products and check their hashes
        all_products = SupplierProduct.objects.all()
        checked_count = 0
        for product in all_products:
            # Use same data structure as the parser expects
            product_data = {
                "description": product.description,
                "product_name": product.product_name,
                "specifications": product.specifications,
                "item_no": product.item_no,
                "variant_id": product.variant_id,
                "variant_width": product.variant_width,
                "variant_length": product.variant_length,
                "variant_price": product.variant_price,
                "price_unit": product.price_unit,
                "supplier_name": product.supplier.name,
            }
            input_hash = parser._calculate_input_hash(product_data)

            if input_hash not in processed_hashes:
                unprocessed.append(product)

            checked_count += 1
            if checked_count % 1000 == 0:
                self.stdout.write(
                    f"  Checked {checked_count}/{all_products.count()} products..."
                )

        return unprocessed
