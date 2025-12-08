"""
SafetyPDFService - PDF generation for JSA/SWP documents.

Generates professional PDF documents from SafetyDocument models
following Morris Sheetmetal branding and NZ WorkSafe guidelines.
"""

import logging
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas

from apps.job.models import SafetyDocument
from apps.workflow.models import CompanyDefaults

logger = logging.getLogger(__name__)


# Page metrics (A4: 210 x 297 mm)
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

styles = getSampleStyleSheet()

# Color palette
PRIMARY = colors.HexColor("#004AAD")  # Morris blue
TEXT_DARK = colors.HexColor("#0F172A")
TEXT_MUTED = colors.HexColor("#334155")
BORDER = colors.HexColor("#CBD5E1")
ROW_ALT = colors.HexColor("#F8FAFC")

# Risk rating colors
RISK_COLORS = {
    "Low": colors.HexColor("#22C55E"),  # Green
    "Moderate": colors.HexColor("#F59E0B"),  # Orange/Amber
    "High": colors.HexColor("#EF4444"),  # Red
    "Extreme": colors.HexColor("#7F1D1D"),  # Dark red
}

# Paragraph styles
title_style = ParagraphStyle(
    "Title",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=20,
    textColor=colors.white,
)

section_header_style = ParagraphStyle(
    "SectionHeader",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=12,
    leading=16,
    textColor=PRIMARY,
    spaceBefore=12,
    spaceAfter=6,
)

body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=13,
    textColor=TEXT_DARK,
)

small_style = ParagraphStyle(
    "Small",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    textColor=TEXT_MUTED,
)


class SafetyPDFService:
    """
    Service for generating PDF documents from SafetyDocument models.
    """

    def __init__(self):
        """Initialize the PDF service."""
        company = CompanyDefaults.objects.first()
        self.company_name = company.company_name if company else "Morris Sheetmetal"

    def create_pdf(self, document: SafetyDocument) -> BytesIO:
        """
        Generate a PDF for a safety document.

        Args:
            document: The SafetyDocument to render

        Returns:
            BytesIO buffer containing the PDF
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        self.page_num = 1
        self.y = PAGE_HEIGHT - MARGIN

        # Draw first page header
        self._draw_header(c, document)

        # Draw document info section
        self._draw_info_section(c, document)

        # Draw PPE section
        self._draw_ppe_section(c, document)

        # Draw tasks section
        self._draw_tasks_section(c, document)

        # Draw additional notes
        if document.additional_notes:
            self._draw_notes_section(c, document)

        # Draw footer on last page
        self._draw_footer(c)

        # Draw page numbers on all pages
        total_pages = self.page_num
        for page_num in range(1, total_pages + 1):
            if page_num > 1:
                c.showPage()
            c.setFont("Helvetica", 8)
            c.setFillColor(TEXT_MUTED)
            c.drawRightString(
                PAGE_WIDTH - MARGIN,
                20,
                f"Page {page_num} of {total_pages}",
            )

        c.save()
        buffer.seek(0)
        return buffer

    def _new_page(self, c: canvas.Canvas, document: SafetyDocument):
        """Start a new page."""
        self._draw_footer(c)
        c.showPage()
        self.page_num += 1
        self.y = PAGE_HEIGHT - MARGIN
        self._draw_header(c, document, continuation=True)

    def _check_space(
        self, c: canvas.Canvas, document: SafetyDocument, needed: float
    ) -> bool:
        """Check if we need a new page and create one if necessary."""
        if self.y - needed < MARGIN + 50:  # Leave room for footer
            self._new_page(c, document)
            return True
        return False

    def _draw_header(
        self, c: canvas.Canvas, document: SafetyDocument, continuation: bool = False
    ):
        """Draw the document header."""
        # Blue header bar
        header_height = 60
        c.setFillColor(PRIMARY)
        c.rect(0, PAGE_HEIGHT - header_height, PAGE_WIDTH, header_height, fill=True)

        # Document type and title
        doc_type = (
            "JOB SAFETY ANALYSIS"
            if document.document_type == "jsa"
            else "SAFE WORK PROCEDURE"
        )
        if continuation:
            doc_type += " (continued)"

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(MARGIN, PAGE_HEIGHT - 25, doc_type)

        c.setFont("Helvetica", 12)
        # Truncate title if too long
        title = (
            document.title[:60] + "..." if len(document.title) > 60 else document.title
        )
        c.drawString(MARGIN, PAGE_HEIGHT - 45, title)

        # Company name on right
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 25, self.company_name)

        # Document ID and date
        c.setFont("Helvetica", 8)
        date_str = document.created_at.strftime("%d/%m/%Y")
        c.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 45, f"Date: {date_str}")

        self.y = PAGE_HEIGHT - header_height - 15

    def _draw_info_section(self, c: canvas.Canvas, document: SafetyDocument):
        """Draw the document information section."""
        self._check_space(c, document, 100)

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(PRIMARY)
        c.drawString(MARGIN, self.y, "DOCUMENT INFORMATION")
        self.y -= 20

        # Info grid
        info_items = [
            ("Site Location:", document.site_location or "To be confirmed"),
            ("Company:", document.company_name),
        ]

        if document.document_type == "jsa" and document.job:
            info_items.insert(0, ("Job Number:", document.job.job_number))
            if document.job.client:
                info_items.append(("Client:", document.job.client.name))

        c.setFont("Helvetica", 10)
        for label, value in info_items:
            c.setFillColor(TEXT_MUTED)
            c.drawString(MARGIN, self.y, label)
            c.setFillColor(TEXT_DARK)
            c.drawString(MARGIN + 100, self.y, str(value)[:60])
            self.y -= 15

        # Description
        self.y -= 10
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(PRIMARY)
        c.drawString(MARGIN, self.y, "Description:")
        self.y -= 15

        # Wrap description text
        desc = document.description or "No description provided"
        c.setFont("Helvetica", 10)
        c.setFillColor(TEXT_DARK)
        self._draw_wrapped_text(c, desc, MARGIN, self.y, CONTENT_WIDTH)

    def _draw_wrapped_text(
        self, c: canvas.Canvas, text: str, x: float, y: float, max_width: float
    ):
        """Draw wrapped text and update self.y."""
        words = text.split()
        lines = []
        current_line = ""

        c.setFont("Helvetica", 10)
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if c.stringWidth(test_line, "Helvetica", 10) < max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        for line in lines:
            c.drawString(x, self.y, line)
            self.y -= 13

    def _draw_ppe_section(self, c: canvas.Canvas, document: SafetyDocument):
        """Draw the PPE requirements section."""
        self._check_space(c, document, 80)

        self.y -= 15
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(PRIMARY)
        c.drawString(MARGIN, self.y, "PERSONAL PROTECTIVE EQUIPMENT (PPE)")
        self.y -= 20

        ppe_items = document.ppe_requirements or []
        if not ppe_items:
            c.setFont("Helvetica-Oblique", 10)
            c.setFillColor(TEXT_MUTED)
            c.drawString(MARGIN, self.y, "No specific PPE requirements listed")
            self.y -= 15
            return

        # Draw PPE items in two columns
        col_width = CONTENT_WIDTH / 2
        c.setFont("Helvetica", 10)
        c.setFillColor(TEXT_DARK)

        for i, ppe in enumerate(ppe_items):
            col = i % 2
            x = MARGIN + (col * col_width)
            c.drawString(x, self.y, f"• {ppe}")
            if col == 1:
                self.y -= 15
        if len(ppe_items) % 2 == 1:
            self.y -= 15

    def _draw_tasks_section(self, c: canvas.Canvas, document: SafetyDocument):
        """Draw the tasks section with hazards and controls."""
        self.y -= 15
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(PRIMARY)
        c.drawString(MARGIN, self.y, "TASK BREAKDOWN")
        self.y -= 20

        tasks = document.tasks or []
        if not tasks:
            c.setFont("Helvetica-Oblique", 10)
            c.setFillColor(TEXT_MUTED)
            c.drawString(MARGIN, self.y, "No tasks defined")
            self.y -= 15
            return

        for task in tasks:
            self._draw_task(c, document, task)

    def _draw_task(self, c: canvas.Canvas, document: SafetyDocument, task: dict):
        """Draw a single task with its hazards and controls."""
        # Estimate space needed for task
        hazards = task.get("potential_hazards", [])
        controls = task.get("control_measures", [])
        estimated_height = 80 + (len(hazards) * 15) + (len(controls) * 15)

        self._check_space(c, document, min(estimated_height, 200))

        step_num = task.get("step_number", "")
        description = task.get("description", "")
        initial_risk = task.get("initial_risk_rating", "")
        revised_risk = task.get("revised_risk_rating", "")

        # Task header with step number
        self.y -= 10
        c.setFillColor(ROW_ALT)
        c.rect(MARGIN, self.y - 5, CONTENT_WIDTH, 22, fill=True, stroke=False)

        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(TEXT_DARK)
        c.drawString(MARGIN + 5, self.y, f"Step {step_num}: {description[:70]}")

        # Risk badges
        self._draw_risk_badge(
            c, PAGE_WIDTH - MARGIN - 120, self.y, initial_risk, "Before"
        )
        self._draw_risk_badge(
            c, PAGE_WIDTH - MARGIN - 55, self.y, revised_risk, "After"
        )

        self.y -= 25

        # Hazards
        if hazards:
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(TEXT_MUTED)
            c.drawString(MARGIN + 10, self.y, "Hazards:")
            self.y -= 12

            c.setFont("Helvetica", 9)
            c.setFillColor(TEXT_DARK)
            for hazard in hazards:
                self._check_space(c, document, 15)
                c.drawString(MARGIN + 20, self.y, f"• {hazard[:80]}")
                self.y -= 12

        # Controls
        if controls:
            self.y -= 5
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(TEXT_MUTED)
            c.drawString(MARGIN + 10, self.y, "Controls:")
            self.y -= 12

            c.setFont("Helvetica", 9)
            c.setFillColor(TEXT_DARK)
            for control in controls:
                self._check_space(c, document, 15)
                if isinstance(control, dict):
                    measure = control.get("measure", "")
                    hazard = control.get("associated_hazard", "")
                    text = f"• {measure}"
                    if hazard:
                        text += f" [{hazard[:30]}]"
                else:
                    text = f"• {control}"
                c.drawString(MARGIN + 20, self.y, text[:90])
                self.y -= 12

        self.y -= 10

    def _draw_risk_badge(
        self, c: canvas.Canvas, x: float, y: float, rating: str, label: str
    ):
        """Draw a color-coded risk rating badge."""
        if not rating:
            return

        color = RISK_COLORS.get(rating, TEXT_MUTED)
        badge_width = 50
        badge_height = 16

        # Badge background
        c.setFillColor(color)
        c.roundRect(x, y - 3, badge_width, badge_height, 3, fill=True, stroke=False)

        # Badge text
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x + badge_width / 2, y + 2, rating[:3])

    def _draw_notes_section(self, c: canvas.Canvas, document: SafetyDocument):
        """Draw additional notes section."""
        self._check_space(c, document, 80)

        self.y -= 15
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(PRIMARY)
        c.drawString(MARGIN, self.y, "ADDITIONAL NOTES")
        self.y -= 15

        c.setFont("Helvetica", 10)
        c.setFillColor(TEXT_DARK)
        self._draw_wrapped_text(
            c, document.additional_notes, MARGIN, self.y, CONTENT_WIDTH
        )

    def _draw_footer(self, c: canvas.Canvas):
        """Draw the document footer."""
        footer_y = 35

        # Separator line
        c.setStrokeColor(BORDER)
        c.line(MARGIN, footer_y + 15, PAGE_WIDTH - MARGIN, footer_y + 15)

        # Footer text
        c.setFont("Helvetica", 7)
        c.setFillColor(TEXT_MUTED)
        c.drawString(
            MARGIN,
            footer_y,
            "This document complies with NZ Health and Safety at Work Act 2015.",
        )
        c.drawString(
            MARGIN,
            footer_y - 10,
            "Review and update as conditions change. All workers must be briefed on contents.",
        )
