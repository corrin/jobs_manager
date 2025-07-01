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
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from apps.job.models import Job

logger = logging.getLogger(__name__)

# A4 page dimensions (210 x 297 mm)
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 50
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

styles = getSampleStyleSheet()
description_style = styles["Normal"]

ImageFile.LOAD_TRUNCATED_IMAGES = True


def wait_until_file_ready(file_path, max_wait=10):
    """Try to open the file."""
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
    """Gets the image dimensions and scales it if larger than content width."""
    wait_until_file_ready(image_path)
    with Image.open(image_path) as img:
        img_width, img_height = img.size
        # Considering 1 pixel = 1 point
        img_width_pt, img_height_pt = img_width, img_height

        if img_width_pt > CONTENT_WIDTH:
            scale = CONTENT_WIDTH / img_width_pt
            img_width_pt = CONTENT_WIDTH
            img_height_pt *= scale

        return img_width_pt, img_height_pt


def convert_html_to_reportlab(html_content):
    """
    Converts HTML from Quill editor to ReportLab-compatible XML format,
    with enhanced support for lists.
    """
    if not html_content:
        return "N/A"

    # Clean specific Quill elements
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

    # First, proccess lists separately
    def process_list(match, list_type):
        list_content = match.group(1)
        # Extract all list items
        items = re.findall(r"<li[^>]*>(.*?)</li>", list_content, re.DOTALL)

        # Format items for ReportLab
        result = "<br/>"
        for i, item in enumerate(items):
            # Use the correct prefix based on list type
            if list_type == "ol":
                prefix = f"{i + 1}. "
            else:  # list_type == "ul"
                prefix = "• "
            result += f"{prefix}{item}<br/>"
        return result

    # Process each list type separately and explicitly
    # Ordered lists - explicitly pass "ol" as list_type
    html_content = re.sub(
        r"<ol[^>]*>(.*?)</ol>",
        lambda m: process_list(m, "ol"),
        html_content,
        flags=re.DOTALL,
    )

    # Unordered lists - explicitly pass "ul" as list_type
    html_content = re.sub(
        r"<ul[^>]*>(.*?)</ul>",
        lambda m: process_list(m, "ul"),
        html_content,
        flags=re.DOTALL,
    )

    # Now process the remaining tags
    replacements = [
        # Text formatting
        (r"<strong>(.*?)</strong>", r"<b>\1</b>"),
        (r"<b>(.*?)</b>", r"<b>\1</b>"),
        (r"<em>(.*?)</em>", r"<i>\1</i>"),
        (r"<i>(.*?)</i>", r"<i>\1</i>"),
        (r"<u>(.*?)</u>", r"<u>\1</u>"),
        (r"<s>(.*?)</s>", r"<strike>\1</strike>"),
        (r"<strike>(.*?)</strike>", r"<strike>\1</strike>"),
        # Links
        (r'<a href="(.*?)">(.*?)</a>', r'<link href="\1">\2</link>'),
        # Paragraphs and line breaks
        (r"<p[^>]*>(.*?)</p>", r"\1<br/><br/>"),
        (r"<br[^>]*>", r"<br/>"),
    ]

    # Apply replacements
    for pattern, replacement in replacements:
        html_content = re.sub(pattern, replacement, html_content, flags=re.DOTALL)

    # Clean unsupported tags
    html_content = re.sub(
        r"<(?!/?b|/?i|/?u|/?strike|/?link|br/)[^>]*>", "", html_content
    )

    # Clean extra line breaks
    html_content = re.sub(r"<br/><br/><br/>", r"<br/><br/>", html_content)
    html_content = re.sub(r"<br/><br/>$", "", html_content)

    return html_content


def create_workshop_pdf(job):
    """
    Generates a PDF for the given job, including details and marked files.
    """
    try:
        # Create main document with job details
        main_buffer = create_main_document(job)

        # Get files marked for printing
        files_to_print = job.files.filter(print_on_jobsheet=True)
        if not files_to_print.exists():
            return main_buffer

        # Separate images and PDFs for different handling
        image_files = [f for f in files_to_print if f.mime_type.startswith("image/")]
        pdf_files = [f for f in files_to_print if f.mime_type == "application/pdf"]

        # Process files based on types present
        return process_attachments(main_buffer, image_files, pdf_files)

    except Exception as e:
        logger.error(f"Error creating workshop PDF: {str(e)}")
        raise e


def create_main_document(job):
    """Creates the main document with job details and materials table."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    # Define initial position
    y_position = PAGE_HEIGHT - MARGIN

    # Add logo
    y_position = add_logo(pdf, y_position)

    # Add title
    y_position = add_title(pdf, y_position, job)

    # Add job details table
    y_position = add_job_details_table(pdf, y_position, job)

    # Add materials table
    add_materials_table(pdf, y_position)

    # Save the document
    pdf.save()
    buffer.seek(0)
    return buffer


def add_logo(pdf, y_position):
    """Adds the logo to the PDF and returns the new y_position."""
    logo_path = os.path.join(settings.BASE_DIR, "workflow/static/logo_msm.png")
    if not os.path.exists(logo_path):
        return y_position

    logo = ImageReader(logo_path)
    # Calculate x position to center the image
    x = MARGIN + (CONTENT_WIDTH - 150) / 2  # 150 is the image width
    pdf.drawImage(logo, x, y_position - 150, width=150, height=150, mask="auto")
    return y_position - 200  # Space to avoid overlap


def add_title(pdf, y_position, job):
    """Adds the title to the PDF and returns the new y_position."""
    pdf.setFillColor(colors.HexColor("#004aad"))
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(MARGIN, y_position, f"Workshop Sheet - {job.name}")
    pdf.setFillColor(colors.black)
    return y_position - 30


def add_job_details_table(pdf, y_position, job: Job):
    """Adds the job details table to the PDF and returns the new y_position."""
    job_details = [
        ["Job Number", job.job_number or "N/A"],
        ["Client", job.client.name if job.client else "N/A"],
        ["Contact", job.contact.name if job.contact else "N/A"],
        ["Description", Paragraph(job.description or "N/A", description_style)],
        [
            "Notes",
            Paragraph(
                convert_html_to_reportlab(job.notes) if job.notes else "N/A",
                description_style,
            ),
        ],
        ["Entry date", job.created_at.strftime("%d %b %Y")],
        ["Order number", job.order_number or "N/A"],
    ]

    details_table = Table(job_details, colWidths=[150, CONTENT_WIDTH - 150])
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004aad")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    table_width, table_height = details_table.wrap(CONTENT_WIDTH, PAGE_HEIGHT)
    details_table.drawOn(pdf, MARGIN, y_position - table_height)
    return y_position - table_height - 40


def add_materials_table(pdf, y_position):
    """Adds the materials table to the PDF and returns the new y_position."""
    # Set up the materials table
    materials_data = [["Description", "Quantity", "Comments"]]
    materials_data.extend([["", "", ""] for _ in range(5)])  # Add 5 empty rows

    materials_table = Table(
        materials_data,
        colWidths=[CONTENT_WIDTH * 0.4, CONTENT_WIDTH * 0.2, CONTENT_WIDTH * 0.4],
    )
    materials_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004aad")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    materials_width, materials_height = materials_table.wrap(CONTENT_WIDTH, PAGE_HEIGHT)

    # Check if materials table fits in remaining space
    required_space = 25 + materials_height + 20  # Title (25) + Table + Spacing (20)
    if (y_position - MARGIN) < required_space:
        # Not enough space, create new page
        pdf.showPage()
        y_position = PAGE_HEIGHT - MARGIN

    # Draw the materials section
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(MARGIN, y_position, "Materials Notes")
    y_position -= 25

    materials_table.drawOn(pdf, MARGIN, y_position - materials_height)
    return y_position - materials_height - 20


def create_image_document(image_files):
    """Creates a PDF document with the given images."""
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

            # Center the image
            x = MARGIN + (CONTENT_WIDTH - width) / 2
            y_position = PAGE_HEIGHT - MARGIN - 10

            # Add image with mask='auto' parameter to handle transparency
            pdf.drawImage(file_path, x, y_position - height, width=width, height=height)

            # Add caption in the footer for images
            pdf.setFont("Helvetica-Oblique", 9)
            pdf.drawString(MARGIN, 30, f"File: {job_file.filename}")

            # Add a new page if not the last image
            if i < len(image_files) - 1:
                pdf.showPage()

        except Exception as e:
            logger.error(f"Failed to add image {job_file.filename}: {e}")
            pdf.setFont("Helvetica", 12)
            pdf.drawString(
                MARGIN, PAGE_HEIGHT - MARGIN - 50, f"Error adding image: {str(e)}"
            )

            # Add a new page if not the last image
            if i < len(image_files) - 1:
                pdf.showPage()

    pdf.save()
    image_buffer.seek(0)
    return image_buffer


def process_attachments(main_buffer, image_files, pdf_files):
    """Processes attachments based on file types present."""
    # Case 1: No attachments
    if not image_files and not pdf_files:
        return main_buffer

    # Case 2: Only PDFs, merge directly
    if not image_files and pdf_files:
        return merge_pdfs([main_buffer] + get_pdf_file_paths(pdf_files))

    # Case 3: Has images (with or without PDFs)
    image_buffer = create_image_document(image_files)

    if not pdf_files:
        # Case 3a: Only images
        return merge_pdfs([main_buffer, image_buffer])
    else:
        # Case 3b: Images and PDFs
        return merge_pdfs([main_buffer, image_buffer] + get_pdf_file_paths(pdf_files))


def get_pdf_file_paths(pdf_files):
    """Returns the file paths for the given PDF files."""
    file_paths = []
    for job_file in pdf_files:
        file_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path)
        if os.path.exists(file_path):
            file_paths.append(file_path)
    return file_paths


def merge_pdfs(pdf_sources):
    """
    Merges multiple PDF sources into one.
    Sources can be file paths or BytesIO objects.
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

        # Write the merged PDF to a new buffer
        result_buffer = BytesIO()
        merger.write(result_buffer)
        result_buffer.seek(0)
        return result_buffer

    finally:
        # Ensure we close all buffers except the result
        for buffer in buffers_to_close:
            try:
                buffer.close()
            except:
                pass
