import csv
import logging
import os
import sys
from collections import defaultdict
from decimal import Decimal

from apps.quoting.services.product_parser import populate_all_mappings_with_llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings.base")
import django

django.setup()

from django.db import transaction

from apps.client.models import Client
from apps.quoting.models import SupplierProduct


def validate_and_parse_csv(csv_file_path):
    """
    Reads and validates the CSV file, parsing data into a list of dictionaries.
    This function will raise an exception immediately on any validation or parsing error.
    Returns parsed_data (list of dicts) if successful.
    """
    parsed_data = []

    expected_columns = [
        "product_name",
        "item_no",
        "description",
        "specifications",
        "variant_width",
        "variant_length",
        "variant_price",
        "price_unit",
        "variant_available_stock",
        "variant_id",
        "url",
        "p_timestamp",
        "pp_timestamp",
    ]

    variant_id_seen = defaultdict(list)  # To check for duplicates within CSV

    with open(csv_file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        # Check for missing columns
        missing_columns = [
            col for col in expected_columns if col not in reader.fieldnames
        ]
        if missing_columns:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(missing_columns)}"
            )

        # Check for unexpected columns (optional)
        unexpected_columns = [
            col for col in reader.fieldnames if col not in expected_columns
        ]
        if unexpected_columns:
            logging.warning(
                f"CSV contains unexpected columns which will be ignored: {', '.join(unexpected_columns)}"
            )

        for i, row in enumerate(reader):
            row_num = i + 2  # Account for header row and 0-based index

            # Validate and parse variant_id
            variant_id = row.get("variant_id", "").strip()
            if not variant_id:
                raise ValueError(
                    f"Row {row_num}: 'variant_id' is empty. This field is required for unique identification."
                )

            # Check for duplicate variant_ids within the CSV as we parse
            variant_id_seen[variant_id].append(row_num)
            if len(variant_id_seen[variant_id]) > 1:
                raise ValueError(
                    f"Row {row_num}: Duplicate 'variant_id' '{variant_id}' found. It also appears in row(s): {', '.join(map(str, variant_id_seen[variant_id][:-1]))}. Each variant_id must be unique per supplier."
                )

            # Validate and parse variant_price
            variant_price_str = row.get("variant_price", "").strip()
            variant_price = None
            if variant_price_str:
                variant_price = Decimal(
                    variant_price_str
                )  # Let InvalidOperation propagate

            # Validate and parse variant_available_stock
            variant_available_stock_str = row.get("variant_available_stock", "").strip()
            variant_available_stock = None
            if variant_available_stock_str:
                variant_available_stock = int(
                    variant_available_stock_str
                )  # Let ValueError propagate

            # If no errors for this row, add to parsed_data
            parsed_data.append(
                {
                    "product_name": row["product_name"],
                    "item_no": row["item_no"],
                    "description": row["description"],
                    "specifications": row["specifications"],
                    "variant_width": row["variant_width"],
                    "variant_length": row["variant_length"],
                    "variant_price": variant_price,
                    "price_unit": row["price_unit"],
                    "variant_available_stock": variant_available_stock,
                    "variant_id": variant_id,
                    "url": row["url"],
                    # p_timestamp and pp_timestamp are not model fields, so they are ignored
                }
            )

    return parsed_data


def import_products(csv_file_path):
    SUPPLIER_NAME = "S&T Stainless Limited - acct 2003173"

    logging.info(f"Attempting to import products from: {csv_file_path}")
    logging.info(f"Target supplier: {SUPPLIER_NAME}")

    # Step 1: Validate and parse the CSV file into an in-memory data model
    logging.info("Starting CSV validation and parsing...")
    products_to_import = validate_and_parse_csv(
        csv_file_path
    )  # Let exceptions propagate
    logging.info(
        f"CSV validation successful. {len(products_to_import)} valid product records found. Proceeding with data import."
    )

    # Step 2: Fetch supplier
    supplier = Client.objects.get(
        name=SUPPLIER_NAME
    )  # Let Client.DoesNotExist propagate
    logging.info(f"Successfully found supplier: {supplier.name}")

    imported_count = 0
    updated_count = 0

    # Step 3: Save the parsed data to the database
    # Use a transaction for atomicity. Any unhandled exception will cause rollback.
    with transaction.atomic():
        for i, product_data in enumerate(products_to_import):
            row_num = i + 2  # Original row number in CSV (approx)

            # Add supplier to product_data
            product_data["supplier"] = supplier

            # Use update_or_create which internally calls .save()
            # Let IntegrityError or other database errors propagate
            obj, created = SupplierProduct.objects.update_or_create(
                supplier=supplier,
                variant_id=product_data["variant_id"],
                defaults=product_data,
            )
            if created:
                imported_count += 1
                logging.info(
                    f"Imported new product (row {row_num}): {obj.product_name} ({obj.variant_id})"
                )
            else:
                updated_count += 1
                logging.info(
                    f"Updated existing product (row {row_num}): {obj.product_name} ({obj.variant_id})"
                )

    logging.info(
        f"Successfully imported {imported_count} new products and updated {updated_count} existing products."
    )

    # Batch process all new mappings with LLM
    populate_all_mappings_with_llm()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logging.critical(
            "Usage: python scripts/import_supplier_products_one_off.py <path_to_csv_file>"
        )
        sys.exit(1)  # Keep this exit for incorrect usage

    csv_file = sys.argv[1]
    import_products(csv_file)
