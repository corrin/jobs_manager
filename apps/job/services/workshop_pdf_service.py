import logging
import os
import re
import time
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageFile
from PyPDF2 import PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from apps.job.models import Job
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


def get_workshop_hours(job: Job) -> float:
    """
    Calculate workshop time allocated from the latest estimate or quote.

    Sums all time CostLines except those ending in "office time" (case-insensitive).
    Falls back to quote if estimate has zero workshop hours.
    """
    estimate = job.cost_sets.filter(kind="estimate").order_by("-rev").first()
    if not estimate:
        exc = ValueError(f"Job {job.job_number} has no estimate CostSet")
        persist_app_error(exc)
        raise exc

    lines = estimate.cost_lines.filter(kind="time").exclude(
        desc__iendswith=" office time"
    )
    workshop_hours = sum(float(line.quantity) for line in lines)

    if workshop_hours <= 0:
        quote = job.cost_sets.filter(kind="quote").order_by("-rev").first()
        if not quote:
            exc = ValueError(
                f"Job {job.job_number} has no quote CostSet to fall back to"
            )
            persist_app_error(exc)
            raise exc

        lines = quote.cost_lines.filter(kind="time").exclude(
            desc__iendswith=" office time"
        )
        workshop_hours = sum(float(line.quantity) for line in lines)

    return workshop_hours


# Page metrics (A4: 210 x 297 mm)
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 50
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

styles = getSampleStyleSheet()

# Palette and typography
PRIMARY = colors.HexColor("#004AAD")
TEXT_DARK = colors.HexColor("#0F172A")
TEXT_MUTED = colors.HexColor("#334155")
BORDER = colors.HexColor("#CBD5E1")
ROW_ALT = colors.HexColor("#F8FAFC")

# Paragraph styles for table content
header_client_style = ParagraphStyle(
    "HeaderClient",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=18,
    leading=22,
    textColor=colors.white,
    spaceAfter=0,
)

header_contact_style = ParagraphStyle(
    "HeaderContact",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=18,
    textColor=colors.white,
    spaceAfter=0,
)

label_style = ParagraphStyle(
    "Label",
    parent=styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=14,
    textColor=TEXT_MUTED,
    spaceAfter=0,
)

body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=14,
    textColor=TEXT_DARK,
)

# Keep the public name expected elsewhere in the file
description_style = body_style

ImageFile.LOAD_TRUNCATED_IMAGES = True


def wait_until_file_ready(file_path, max_wait=10):
    """Wait until the file is readable, up to max_wait seconds."""
    wait_time = 0
    while wait_time < max_wait:
        try:
            with open(file_path, "rb") as f:
                f.read(10)
            return
        except OSError:
            time.sleep(1)
            wait_time += 1


def get_image_dimensions(image_path):
    """Return image dimensions in points, scaled to fit CONTENT_WIDTH."""
    wait_until_file_ready(image_path)
    with Image.open(image_path) as img:
        img_width, img_height = img.size
        img_width_pt, img_height_pt = img_width, img_height
        if img_width_pt > CONTENT_WIDTH:
            scale = CONTENT_WIDTH / img_width_pt
            img_width_pt = CONTENT_WIDTH
            img_height_pt *= scale
        return img_width_pt, img_height_pt


def convert_html_to_reportlab(html_content):
    """
    Convert Quill HTML to ReportLab-friendly inline markup, with list support.
    """
    if not html_content:
        return "N/A"

    html_content = re.sub(r'<span class="ql-ui"[^>]*>.*?</span>', "", html_content)
    html_content = re.sub(r' data-list="[^"]*"', "", html_content)
    html_content = re.sub(r' contenteditable="[^"]*"', "", html_content)

    html_content = re.sub(
        r"<h1[^>]*>(.*?)</h1>",
        r'<font size="18"><b>\1</b></font><br/><br/>',
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(
        r"<h2[^>]*>(.*?)</h2>",
        r'<font size="16"><b>\1</b></font><br/><br/>',
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(
        r"<h3[^>]*>(.*?)</h3>",
        r'<font size="14"><b>\1</b></font><br/><br/>',
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(
        r"<h4[^>]*>(.*?)</h4>",
        r'<font size="13"><b>\1</b></font><br/><br/>',
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(
        r"<blockquote[^>]*>(.*?)</blockquote>",
        r"<i>\1</i><br/><br/>",
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(
        r"<pre[^>]*>(.*?)</pre>",
        r'<font face="Courier">\1</font><br/><br/>',
        html_content,
        flags=re.DOTALL,
    )

    def process_list(match, list_type):
        list_content = match.group(1)
        items = re.findall(r"<li[^>]*>(.*?)</li>", list_content, re.DOTALL)
        result = "<br/>"
        for i, item in enumerate(items):
            prefix = f"{i + 1}. " if list_type == "ol" else "• "
            result += f"{prefix}{item}<br/>"
        return result

    html_content = re.sub(
        r"<ol[^>]*>(.*?)</ol>",
        lambda m: process_list(m, "ol"),
        html_content,
        flags=re.DOTALL,
    )
    html_content = re.sub(
        r"<ul[^>]*>(.*?)</ul>",
        lambda m: process_list(m, "ul"),
        html_content,
        flags=re.DOTALL,
    )

    replacements = [
        (r"<strong>(.*?)</strong>", r"<b>\1</b>"),
        (r"<b>(.*?)</b>", r"<b>\1</b>"),
        (r"<em>(.*?)</em>", r"<i>\1</i>"),
        (r"<i>(.*?)</i>", r"<i>\1</i>"),
        (r"<u>(.*?)</u>", r"<u>\1</u>"),
        (r"<s>(.*?)</s>", r"<strike>\1</strike>"),
        (r"<strike>(.*?)</strike>", r"<strike>\1</strike>"),
        (r'<a href="(.*?)">(.*?)</a>', r'<link href="\1">\2</link>'),
        (r"<p[^>]*>(.*?)</p>", r"\1<br/><br/>"),
        (r"<br[^>]*>", r"<br/>"),
    ]
    for pattern, replacement in replacements:
        html_content = re.sub(pattern, replacement, html_content, flags=re.DOTALL)

    html_content = re.sub(
        r"<(?!/?b|/?i|/?u|/?strike|/?link|br/)[^>]*>", "", html_content
    )
    html_content = re.sub(r"<br/><br/><br/>", r"<br/><br/>", html_content)
    html_content = re.sub(r"<br/><br/>$", "", html_content)
    return html_content


def create_workshop_pdf(job):
    """
    Generate the main PDF and, if any, append marked images and PDFs.
    """
    try:
        main_buffer = create_main_document(job)

        files_to_print = job.files.filter(print_on_jobsheet=True)
        if not files_to_print.exists():
            return main_buffer

        image_files = [f for f in files_to_print if f.mime_type.startswith("image/")]
        pdf_files = [f for f in files_to_print if f.mime_type == "application/pdf"]

        return process_attachments(main_buffer, image_files, pdf_files)
    except Exception as e:
        logger.error(f"Error creating workshop PDF: {str(e)}")
        raise e


def create_main_document(job):
    """Create the cover document with header, details, and materials table."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    y_position = PAGE_HEIGHT - MARGIN
    y_position = add_logo(pdf, y_position)
    y_position = add_title(pdf, y_position, job)
    y_position = add_job_details_table(pdf, y_position, job)
    add_materials_table(pdf, y_position)

    pdf.save()
    buffer.seek(0)
    return buffer


def add_logo(pdf, y_position):
    """Draw the logo centred at the top and return the updated y position."""
    logo_path = os.path.join(settings.BASE_DIR, "jobs_manager/logo_msm.png")
    if not os.path.exists(logo_path):
        return y_position
    logo = ImageReader(logo_path)
    x = MARGIN + (CONTENT_WIDTH - 150) / 2
    pdf.drawImage(logo, x, y_position - 150, width=150, height=150, mask="auto")
    return y_position - 200


def add_title(pdf, y_position, job):
    """Render the job title with consistent palette."""
    pdf.setFillColor(PRIMARY)
    pdf.setFont("Helvetica-Bold", 18)
    job_number = str(job.job_number) if job.job_number else "N/A"
    job_name = job.name or "N/A"
    pdf.drawString(MARGIN, y_position, f"Job - {job_number} - {job_name}")
    pdf.setFillColor(colors.black)
    return y_position - 28


def add_job_details_table(pdf, y_position, job: Job):
    """Render the job details with a coloured header row and improved spacing."""
    client_name = job.client.name if job.client else "N/A"
    contact_name = job.contact.name if job.contact else ""

    contact_phone = (
        (job.contact.phone if job.contact and job.contact.phone else None)
        or (job.client.phone if job.client else None)
        or ""
    )
    contact_info = (
        f"{contact_name}<br/>{contact_phone}" if contact_phone else contact_name
    )

    workshop_hours = get_workshop_hours(job)
    pricing_suffix = (
        " (T&M)" if job.pricing_methodology == "time_materials" else " (Quoted)"
    )
    workshop_display = f"{workshop_hours:.1f} hours{pricing_suffix}"

    # Use Paragraph styles so header text is white over the blue background
    job_details = [
        [
            Paragraph(client_name, header_client_style),
            Paragraph(contact_info, header_contact_style),
        ],
        [
            Paragraph("DESCRIPTION", label_style),
            Paragraph(job.description or "N/A", body_style),
        ],
        [
            Paragraph("WORKSHOP TIME ALLOCATED", label_style),
            Paragraph(workshop_display, body_style),
        ],
        [
            Paragraph("NOTES", label_style),
            Paragraph(
                convert_html_to_reportlab(job.notes) if job.notes else "N/A", body_style
            ),
        ],
        [Paragraph("ENTRY DATE", label_style), job.created_at.strftime("%a, %d %b %Y")],
        [
            Paragraph("DUE DATE", label_style),
            job.delivery_date.strftime("%a, %d %b %Y") if job.delivery_date else "N/A",
        ],
        [
            Paragraph("ORDER NUMBER", label_style),
            Paragraph(job.order_number or "N/A", body_style),
        ],
    ]

    details_table = Table(job_details, colWidths=[180, CONTENT_WIDTH - 180])
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 1), (0, -1), TEXT_MUTED),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ]
        )
    )

    _, table_height = details_table.wrap(CONTENT_WIDTH, PAGE_HEIGHT)
    details_table.drawOn(pdf, MARGIN, y_position - table_height)
    return y_position - table_height - 36


def add_materials_table(pdf, y_position):
    """Render the materials notes table with a consistent header and zebra rows."""
    materials_data = [["DESCRIPTION", "QUANTITY", "COMMENTS"]]
    materials_data.extend([["", "", ""] for _ in range(5)])

    materials_table = Table(
        materials_data,
        colWidths=[CONTENT_WIDTH * 0.4, CONTENT_WIDTH * 0.2, CONTENT_WIDTH * 0.4],
    )
    materials_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
            ]
        )
    )

    materials_width, materials_height = materials_table.wrap(
        CONTENT_WIDTH, PAGE_HEIGHT
    )  # noqa: F841

    required_space = 25 + materials_height + 20
    if (y_position - MARGIN) < required_space:
        pdf.showPage()
        y_position = PAGE_HEIGHT - MARGIN

    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(TEXT_DARK)
    pdf.drawString(MARGIN, y_position, "Materials Notes")
    y_position -= 25

    materials_table.drawOn(pdf, MARGIN, y_position - materials_height)
    return y_position - materials_height - 20


def create_image_document(image_files):
    """Create a PDF containing the selected images, one per page."""
    if not image_files:
        return None

    image_buffer = BytesIO()
    pdf = canvas.Canvas(image_buffer, pagesize=A4)

    for i, job_file in enumerate(image_files):
        file_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path)
        if not os.path.exists(file_path):
            continue

        try:
            width, height = get_image_dimensions(file_path)
            x = MARGIN + (CONTENT_WIDTH - width) / 2
            y_position = PAGE_HEIGHT - MARGIN - 10
            pdf.drawImage(file_path, x, y_position - height, width=width, height=height)

            pdf.setFont("Helvetica-Oblique", 9)
            pdf.drawString(MARGIN, 30, f"File: {job_file.filename}")

            if i < len(image_files) - 1:
                pdf.showPage()
        except Exception as e:
            logger.error(f"Failed to add image {job_file.filename}: {e}")
            pdf.setFont("Helvetica", 12)
            pdf.drawString(
                MARGIN, PAGE_HEIGHT - MARGIN - 50, f"Error adding image: {str(e)}"
            )
            if i < len(image_files) - 1:
                pdf.showPage()

    pdf.save()
    image_buffer.seek(0)
    return image_buffer


def process_attachments(main_buffer, image_files, pdf_files):
    """Append images and/or external PDFs to the main document."""
    if not image_files and not pdf_files:
        return main_buffer

    if not image_files and pdf_files:
        return merge_pdfs([main_buffer] + get_pdf_file_paths(pdf_files))

    image_buffer = create_image_document(image_files)
    if not pdf_files:
        return merge_pdfs([main_buffer, image_buffer])

    return merge_pdfs([main_buffer, image_buffer] + get_pdf_file_paths(pdf_files))


def get_pdf_file_paths(pdf_files):
    """Resolve absolute paths for PDF attachments on disk."""
    file_paths = []
    for job_file in pdf_files:
        file_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path)
        if os.path.exists(file_path):
            file_paths.append(file_path)
    return file_paths


def merge_pdfs(pdf_sources):
    """
    Merge multiple PDFs (BytesIO or file paths) into a single buffer.
    """
    merger = PdfWriter()
    buffers_to_close = []

    try:
        for source in pdf_sources:
            try:
                if isinstance(source, BytesIO):
                    merger.append(source)
                    buffers_to_close.append(source)
                else:
                    merger.append(source)
            except Exception as e:
                logger.error(f"Failed to merge PDF: {e}")

        result_buffer = BytesIO()
        merger.write(result_buffer)
        result_buffer.seek(0)
        return result_buffer
    finally:
        for buffer in buffers_to_close:
            try:
                buffer.close()
            except Exception as e:
                logger.error(f"Error closing buffer: {str(e)}")
                persist_app_error(e)
