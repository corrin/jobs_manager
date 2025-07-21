import logging
import os
from io import BytesIO

from django.conf import settings
from PIL import ImageFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

logger = logging.getLogger(__name__)

# A4 page dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 50
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

# Initialize styles
styles = getSampleStyleSheet()
normal_style = styles["Normal"]
bold_style = styles["Heading4"]
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Primary color for headers
PRIMARY_COLOR = colors.HexColor("#000080")  # Navy blue


class PurchaseOrderPDFGenerator:
    """
    Generator class for Purchase Order PDF documents.
    """

    def __init__(self, purchase_order):
        """
        Initialize the PDF generator with a purchase order.

        Args:
            purchase_order: The PurchaseOrder model instance to generate PDF for
        """
        self.purchase_order = purchase_order
        self.buffer = BytesIO()
        self.pdf = canvas.Canvas(self.buffer, pagesize=A4)
        self.y_position = PAGE_HEIGHT - MARGIN

    def generate(self):
        """
        Generate the complete PDF document.
        Returns:
            BytesIO: Buffer containing the generated PDF
        """
        try:
            # Add content to PDF
            self.y_position = self.add_logo(self.y_position)
            self.y_position = self.add_header_info(self.y_position)
            self.y_position = self.add_supplier_info(self.y_position)
            self.y_position = self.add_line_items_table(self.y_position)

            # Save PDF and return buffer
            self.pdf.save()
            self.buffer.seek(0)
            return self.buffer

        except Exception as e:
            logger.exception(
                f"Error generating PDF for PO {self.purchase_order.id}: {str(e)}"
            )
            raise

    def add_logo(self, y_position):
        """Add company logo to the PDF."""
        # Use the specific logo path within jobs_manager
        logo_path = os.path.join(settings.BASE_DIR, "jobs_manager", "logo_msm.png")

        if not os.path.exists(logo_path):
            logger.warning(f"Logo file not found at: {logo_path}")
            # Add company name as text instead of logo
            self.pdf.setFont("Helvetica-Bold", 16)
            self.pdf.setFillColor(PRIMARY_COLOR)
            self.pdf.drawString(
                PAGE_WIDTH - MARGIN - 150, y_position - 20, "MSM Company"
            )
            self.pdf.setFillColor(colors.black)
            return y_position - 30

        try:
            logger.info(f"Using logo at: {logo_path}")
            logo = ImageReader(logo_path)
            # Position logo in top right corner
            self.pdf.drawImage(
                logo,
                PAGE_WIDTH - MARGIN - 120,  # X position (right aligned)
                y_position - 80,  # Y position
                width=120,
                height=80,
                preserveAspectRatio=True,
                mask="auto",
            )
            return y_position - 90
        except Exception as e:
            logger.warning(f"Failed to load logo from {logo_path}: {str(e)}")
            # Fallback to company name
            self.pdf.setFont("Helvetica-Bold", 16)
            self.pdf.setFillColor(PRIMARY_COLOR)
            self.pdf.drawString(
                PAGE_WIDTH - MARGIN - 150, y_position - 20, "MSM Company"
            )
            self.pdf.setFillColor(colors.black)
            return y_position - 30

    def add_header_info(self, y_position):
        """Add purchase order header and details to the PDF."""
        # Main title
        self.pdf.setFont("Helvetica-Bold", 18)
        self.pdf.setFillColor(PRIMARY_COLOR)
        self.pdf.drawString(MARGIN, y_position, "PURCHASE ORDER")
        y_position -= 30

        # Reset color for rest of content
        self.pdf.setFillColor(colors.black)

        # PO Number and Date - in two columns
        self.pdf.setFont("Helvetica-Bold", 12)
        self.pdf.drawString(MARGIN, y_position, "PO Number:")
        self.pdf.setFont("Helvetica", 12)
        self.pdf.drawString(MARGIN + 80, y_position, str(self.purchase_order.po_number))

        # Order date on the right
        self.pdf.setFont("Helvetica-Bold", 12)
        self.pdf.drawString(PAGE_WIDTH - MARGIN - 120, y_position, "Order Date:")
        self.pdf.setFont("Helvetica", 12)
        order_date = (
            self.purchase_order.order_date.strftime("%d/%m/%Y")
            if self.purchase_order.order_date
            else "N/A"
        )
        self.pdf.drawString(PAGE_WIDTH - MARGIN - 50, y_position, order_date)
        y_position -= 20

        # Expected delivery
        if self.purchase_order.expected_delivery:
            self.pdf.setFont("Helvetica-Bold", 12)
            self.pdf.drawString(MARGIN, y_position, "Expected Delivery:")
            self.pdf.setFont("Helvetica", 12)
            delivery_date = self.purchase_order.expected_delivery.strftime("%d/%m/%Y")
            self.pdf.drawString(MARGIN + 120, y_position, delivery_date)
            y_position -= 20

        # Reference if available
        if self.purchase_order.reference:
            self.pdf.setFont("Helvetica-Bold", 12)
            self.pdf.drawString(MARGIN, y_position, "Reference:")
            self.pdf.setFont("Helvetica", 12)
            self.pdf.drawString(
                MARGIN + 80, y_position, str(self.purchase_order.reference)
            )
            y_position -= 20

        return y_position - 10

    def add_supplier_info(self, y_position):
        """Add supplier information section to the PDF."""
        if not self.purchase_order.supplier:
            return y_position

        # Supplier section header
        self.pdf.setFont("Helvetica-Bold", 14)
        self.pdf.setFillColor(PRIMARY_COLOR)
        self.pdf.drawString(MARGIN, y_position, "Supplier Information")
        self.pdf.setFillColor(colors.black)
        y_position -= 25

        supplier = self.purchase_order.supplier

        # Supplier name
        self.pdf.setFont("Helvetica-Bold", 12)
        self.pdf.drawString(MARGIN, y_position, "Name:")
        self.pdf.setFont("Helvetica", 12)
        self.pdf.drawString(MARGIN + 50, y_position, supplier.name)
        y_position -= 20

        # Supplier email
        if supplier.email:
            self.pdf.setFont("Helvetica-Bold", 12)
            self.pdf.drawString(MARGIN, y_position, "Email:")
            self.pdf.setFont("Helvetica", 12)
            self.pdf.drawString(MARGIN + 50, y_position, supplier.email)
            y_position -= 20

        # Supplier phone
        if supplier.phone:
            self.pdf.setFont("Helvetica-Bold", 12)
            self.pdf.drawString(MARGIN, y_position, "Phone:")
            self.pdf.setFont("Helvetica", 12)
            self.pdf.drawString(MARGIN + 50, y_position, supplier.phone)
            y_position -= 20

        return y_position - 10

    def add_line_items_table(self, y_position):
        """Add the table of purchase order line items."""
        # Table header
        self.pdf.setFont("Helvetica-Bold", 14)
        self.pdf.setFillColor(PRIMARY_COLOR)
        self.pdf.drawString(MARGIN, y_position, "Order Items")
        self.pdf.setFillColor(colors.black)
        y_position -= 25

        # Get line items
        line_items = self.purchase_order.po_lines.all()

        if not line_items.exists():
            self.pdf.setFont("Helvetica", 12)
            self.pdf.drawString(MARGIN, y_position, "No items in this purchase order.")
            return y_position - 20

        # Check if any line items have additional fields to determine table structure
        has_additional_fields = any(
            item.metal_type
            or item.alloy
            or item.specifics
            or item.location
            or item.dimensions
            for item in line_items
        )

        # Prepare table headers based on available data
        if has_additional_fields:
            table_data = [
                [
                    "Item Code",
                    "Description",
                    "Additional Info",
                    "Qty",
                    "Unit Cost",
                    "Total",
                ],
            ]
            col_widths = [
                CONTENT_WIDTH * 0.15,  # Item Code
                CONTENT_WIDTH * 0.35,  # Description
                CONTENT_WIDTH * 0.25,  # Additional Info
                CONTENT_WIDTH * 0.1,  # Qty
                CONTENT_WIDTH * 0.075,  # Unit Cost
                CONTENT_WIDTH * 0.075,  # Total
            ]
        else:
            table_data = [
                ["Item Code", "Description", "Qty", "Unit Cost", "Total"],
            ]
            col_widths = [
                CONTENT_WIDTH * 0.2,  # Item Code
                CONTENT_WIDTH * 0.5,  # Description
                CONTENT_WIDTH * 0.1,  # Qty
                CONTENT_WIDTH * 0.1,  # Unit Cost
                CONTENT_WIDTH * 0.1,  # Total
            ]

        total_amount = 0

        for item in line_items:
            line_total = (
                float(item.quantity * item.unit_cost)
                if item.quantity and item.unit_cost
                else 0
            )
            total_amount += line_total

            # Build additional info only if fields are present
            additional_info_parts = []
            if item.metal_type:
                additional_info_parts.append(f"Metal: {item.metal_type}")
            if item.alloy:
                additional_info_parts.append(f"Alloy: {item.alloy}")
            if item.specifics:
                additional_info_parts.append(f"Specs: {item.specifics}")
            if item.location:
                additional_info_parts.append(f"Location: {item.location}")
            if item.dimensions:
                additional_info_parts.append(f"Dimensions: {item.dimensions}")

            additional_info = (
                "\n".join(additional_info_parts) if additional_info_parts else ""
            )

            # Truncate long descriptions
            description = str(item.description or "")[:50] + (
                "..." if len(str(item.description or "")) > 50 else ""
            )
            item_code = str(item.item_code or "")[:20] + (
                "..." if len(str(item.item_code or "")) > 20 else ""
            )

            if has_additional_fields:
                table_data.append(
                    [
                        item_code,
                        description,
                        additional_info[:60]
                        + (
                            "..." if len(additional_info) > 60 else ""
                        ),  # Truncate additional info
                        f"{float(item.quantity):.2f}" if item.quantity else "0.00",
                        f"${float(item.unit_cost):.2f}" if item.unit_cost else "TBC",
                        f"${line_total:.2f}" if not item.price_tbc else "TBC",
                    ]
                )
            else:
                table_data.append(
                    [
                        item_code,
                        description,
                        f"{float(item.quantity):.2f}" if item.quantity else "0.00",
                        f"${float(item.unit_cost):.2f}" if item.unit_cost else "TBC",
                        f"${line_total:.2f}" if not item.price_tbc else "TBC",
                    ]
                )

        # Add total row
        if has_additional_fields:
            table_data.append(["", "", "", "", "TOTAL:", f"${total_amount:.2f}"])
        else:
            table_data.append(["", "", "", "TOTAL:", f"${total_amount:.2f}"])

        # Create table with dynamic column widths
        lines_table = Table(table_data, colWidths=col_widths)

        # Style the table
        table_style = TableStyle(
            [
                # Header styling
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Data rows
                ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -2), 8),
                (
                    "ALIGN",
                    (-3, 1),
                    (-1, -1),
                    "RIGHT",
                ),  # Right align quantity, cost, total columns
                ("ALIGN", (0, 1), (-4, -1), "LEFT"),  # Left align text columns
                ("VALIGN", (0, 1), (-1, -1), "TOP"),  # Top align for multi-line content
                # Total row styling
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                # Borders
                ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
                # Padding
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
        lines_table.setStyle(table_style)

        # Check if table fits on current page
        table_width, table_height = lines_table.wrap(CONTENT_WIDTH, PAGE_HEIGHT)
        if y_position - table_height < MARGIN + 50:  # 50 is space for footer
            # Start new page if needed
            self.pdf.showPage()
            y_position = PAGE_HEIGHT - MARGIN
            # Redraw title on new page
            self.pdf.setFont("Helvetica-Bold", 14)
            self.pdf.drawString(MARGIN, y_position, "Order Items (Continued)")
            y_position -= 25

        lines_table.drawOn(self.pdf, MARGIN, y_position - table_height)
        return y_position - table_height - 20


def create_purchase_order_pdf(purchase_order):
    """
    Factory function to generate a PDF for a purchase order.

    Args:
        purchase_order: The PurchaseOrder instance

    Returns:
        BytesIO: Buffer containing the generated PDF
    """
    generator = PurchaseOrderPDFGenerator(purchase_order)
    return generator.generate()
