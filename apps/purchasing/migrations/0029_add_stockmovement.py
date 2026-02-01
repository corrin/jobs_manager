import uuid

import django.db.models.deletion
from django.db import migrations, models


def _dedupe_stock_item_codes(apps, schema_editor):
    Stock = apps.get_model("purchasing", "Stock")
    StockMovement = apps.get_model("purchasing", "StockMovement")

    duplicates = (
        Stock.objects.exclude(item_code__isnull=True)
        .exclude(item_code="")
        .values("item_code")
        .annotate(count=models.Count("id"))
        .filter(count__gt=1)
    )

    for dup in duplicates:
        item_code = dup["item_code"]
        stocks = list(Stock.objects.filter(item_code=item_code).order_by("date", "id"))
        if len(stocks) < 2:
            continue

        primary = stocks[0]
        for other in stocks[1:]:
            # Move child stock splits to the primary
            Stock.objects.filter(source_parent_stock_id=other.id).update(
                source_parent_stock_id=primary.id
            )

            # Update CostLine ext_refs JSON where stock_id matches the duplicate
            with schema_editor.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE job_costline
                    SET ext_refs = JSON_SET(ext_refs, '$.stock_id', %s)
                    WHERE JSON_EXTRACT(ext_refs, '$.stock_id') = %s
                    """,
                    [str(primary.id), str(other.id)],
                )

            # Add quantity to primary (do not change unit_cost)
            if other.quantity:
                primary.quantity += other.quantity
                primary.save(update_fields=["quantity"])

            StockMovement.objects.create(
                stock=primary,
                movement_type="merge",
                quantity_delta=other.quantity,
                unit_cost=other.unit_cost,
                unit_revenue=other.unit_revenue,
                source=other.source,
                source_parent_stock=other,
                metadata={"source_stock_id": str(other.id)},
            )

            other.delete()


def _align_stock_uuid_columns(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DATA_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'workflow_stock'
              AND COLUMN_NAME = 'id'
            """
        )
        row = cursor.fetchone()
        if not row:
            return

        id_type = row[0]

        cursor.execute(
            """
            SELECT DATA_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'workflow_stock'
              AND COLUMN_NAME = 'source_parent_stock_id'
            """
        )
        parent_row = cursor.fetchone()
        parent_type = parent_row[0] if parent_row else None

        if id_type == "uuid" and parent_type == "uuid":
            return

        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'workflow_stock'
              AND COLUMN_NAME = 'source_parent_stock_id'
              AND REFERENCED_TABLE_NAME = 'workflow_stock'
            """
        )
        fk_names = [row[0] for row in cursor.fetchall() if row[0]]

        for fk_name in fk_names:
            cursor.execute(f"ALTER TABLE workflow_stock DROP FOREIGN KEY {fk_name}")

        cursor.execute("ALTER TABLE workflow_stock MODIFY COLUMN id UUID NOT NULL")
        cursor.execute(
            "ALTER TABLE workflow_stock MODIFY COLUMN source_parent_stock_id UUID NULL"
        )

        constraint_name = (
            fk_names[0]
            if fk_names
            else "workflow_stock_source_parent_stock__7633cf27_fk_workflow_"
        )
        cursor.execute(
            "ALTER TABLE workflow_stock "
            f"ADD CONSTRAINT {constraint_name} "
            "FOREIGN KEY (source_parent_stock_id) REFERENCES workflow_stock(id)"
        )


def _backfill_costline_stock_movements(apps, schema_editor):
    Stock = apps.get_model("purchasing", "Stock")
    StockMovement = apps.get_model("purchasing", "StockMovement")
    CostLine = apps.get_model("job", "CostLine")

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, JSON_UNQUOTE(JSON_EXTRACT(ext_refs, '$.stock_id'))
            FROM job_costline
            WHERE JSON_EXTRACT(ext_refs, '$.stock_id') IS NOT NULL
            """
        )
        rows = cursor.fetchall()

    for costline_id, stock_id in rows:
        if not stock_id:
            continue
        try:
            stock = Stock.objects.get(id=stock_id)
        except Stock.DoesNotExist:
            continue

        costline = CostLine.objects.get(id=costline_id)
        qty = costline.quantity or 0

        movement = StockMovement.objects.create(
            stock=stock,
            movement_type="consume",
            quantity_delta=-qty,
            unit_cost=costline.unit_cost,
            unit_revenue=costline.unit_rev,
            source="costline_consume",
            source_cost_line=costline,
            metadata={"backfilled": True},
        )

        ext_refs = costline.ext_refs or {}
        ext_refs.pop("stock_id", None)
        ext_refs["stock_movement_id"] = str(movement.id)
        costline.ext_refs = ext_refs
        costline.save(update_fields=["ext_refs"])


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0067_normalize_wage_rate_multiplier"),
        ("purchasing", "0028_update_created_by_from_events"),
    ]

    operations = [
        migrations.RunPython(
            code=_align_stock_uuid_columns, reverse_code=migrations.RunPython.noop
        ),
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "movement_type",
                    models.CharField(
                        choices=[
                            ("receipt", "Receipt"),
                            ("consume", "Consume"),
                            ("adjust", "Adjust"),
                            ("split", "Split"),
                            ("merge", "Merge"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "quantity_delta",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                (
                    "unit_cost",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "unit_revenue",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("purchase_order", "Purchase Order Receipt"),
                            ("split_from_stock", "Split/Offcut from Stock"),
                            ("manual", "Manual Adjustment/Stocktake"),
                            ("product_catalog", "Product Catalog"),
                            ("costline_consume", "CostLine Consumption"),
                        ],
                        max_length=50,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "source_cost_line",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_movements",
                        to="job.costline",
                    ),
                ),
                (
                    "source_parent_stock",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="child_movements",
                        to="purchasing.stock",
                    ),
                ),
                (
                    "source_purchase_order_line",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_movements",
                        to="purchasing.purchaseorderline",
                    ),
                ),
                (
                    "stock",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movements",
                        to="purchasing.stock",
                    ),
                ),
            ],
            options={
                "db_table": "workflow_stockmovement",
            },
        ),
        migrations.RunPython(
            code=_dedupe_stock_item_codes, reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(
            code=_backfill_costline_stock_movements,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="stockmovement",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(
                        movement_type="receipt",
                        source_purchase_order_line__isnull=False,
                    )
                    | ~models.Q(movement_type="receipt")
                ),
                name="stockmovement_receipt_requires_po_line",
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=["stock", "created_at"], name="stockmove_stock_dt"
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=["movement_type", "created_at"], name="stockmove_type_dt"
            ),
        ),
    ]
