import logging
from io import BytesIO

from django.contrib import messages
from django.contrib.staticfiles.finders import find
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from apps.job.models import Job
from apps.workflow.utils import extract_messages

logger = logging.getLogger(__name__)


def collect_pricing_data(pricing):
    """
    Collects time, material, and adjustment entries from a JobPricing instance.

    Args:
        job_pricing (JobPricing): The JobPricing instance.

    Returns:
        dict: A dictionary containing structured data for time, material,
            and adjustment entries.
    """
    time_entries = [
        [
            "Description",
            "Items",
            "Mins/Item",
            "Total Minutes",
            "Wage Rate",
            "Charge Rate",
        ]
    ]
    material_entries = [
        ["Item Code", "Description", "Quantity", "Cost Rate", "Retail Rate", "Revenue"]
    ]
    adjustment_entries = [["Description", "Cost Adj.", "Revenue", "Comments"]]

    # Collect time entries
    for entry in pricing.time_entries.all():
        time_entries.append(
            [
                entry.description or "N/A",  # BUG
                entry.items or 0,
                (
                    f"{entry.minutes_per_item:.2f}"
                    if entry.minutes_per_item
                    else "0.00"
                ),  # BUG
                f"{entry.minutes:.2f}",
                f"NZD {entry.wage_rate:.2f}",
                f"NZD {entry.charge_out_rate:.2f}",
            ]
        )

    # Collect material entries
    for entry in pricing.material_entries.all():
        material_entries.append(
            [
                entry.item_code or "N/A",  # BUG: NEVER USE "OR".  OR IS A FALLBACK
                entry.description or "N/A",
                f"{entry.quantity:.2f}" if entry.quantity else "0.00",
                f"NZD {entry.unit_cost:.2f}",
                f"NZD {entry.unit_revenue:.2f}",
                f"NZD {entry.revenue:.2f}",
            ]
        )

    # Collect adjustment entries
    for entry in pricing.adjustment_entries.all():
        adjustment_entries.append(
            [
                entry.description or "N/A",  # BUG
                f"NZD {entry.cost_adjustment:.2f}",
                f"NZD {entry.price_adjustment:.2f}",
                entry.comments or "N/A",  # BUG
            ]
        )

    return {
        "time_entries": time_entries,
        "material_entries": material_entries,
        "adjustment_entries": adjustment_entries,
    }


def create_pdf(job):
    """
    Generate a PDF for the given job, including a quotes table.

    Args:
        job: The Job instance for which the PDF will be generated.

    Returns:
        BytesIO: A buffer containing the generated PDF.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    logo_path = find("logo_msm.png")

    try:
        pdf.drawImage(
            logo_path,
            x=420,
            y=680,
            width=150,
            height=100,
            preserveAspectRatio=True,
            mask="auto",
        )
    except Exception as e:
        logger.debug(f"Error loading logo: {e}")

    # Header with job and client information
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, 750, f"Quote Summary for {job.name}")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 720, "Client:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(120, 720, f"{job.client.name if job.client else 'N/A'}")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 700, "Contact:")
    pdf.setFont("Helvetica", 12)
    # BUG.  Fallback! yuck.
    pdf.drawString(
        120,
        700,
        f"{job.client.email or (job.contact.email if job.contact else 'N/A')}",
    )

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 680, "Job Number:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(150, 680, f"{job.job_number if job.job_number else 'N/A'}")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, 660, "Job Description:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(
        150, 660, f"{job.description[:200] if job.description else 'N/A'}..."
    )

    # Add a horizontal line to separate this section from the tables
    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(0.5)
    pdf.line(50, 640, 550, 640)

    start_y = 620

    total_width = 500
    table_styles = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#000080")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ]
    )

    for section, data in collect_pricing_data(job.latest_quote_pricing).items():
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, start_y, section.replace("_", " ").title())

        start_y -= 15

        # Ensure at least 2 rows for visual consistency
        if len(data) < 2:
            data.extend([[""] * len(data[0])] * (2 - len(data)))

        # Custom column widths for specific sections
        if section == "material_entries":
            col_widths = [
                60,
                140,
                60,
                80,
                80,
                80,
            ]  # Adjusted widths: smaller for "Item Code"
        else:
            # Default column widths for other sections
            num_columns = len(data[0])
            total_width = 500
            col_widths = [total_width / num_columns] * num_columns

        # Create table
        table = Table(data, colWidths=col_widths)
        table.setStyle(table_styles)

        # Calculate table height
        table_width, table_height = table.wrap(0, 0)

        # Adjust position based on table height
        if start_y - table_height < 50:  # Ensure space for the footer
            pdf.showPage()
            start_y = 750  # Reset start position on new page

        table.wrapOn(pdf, 50, start_y)
        table.drawOn(pdf, 50, start_y - table_height)
        start_y -= table_height + 45

        # Add a horizontal line between tables
        pdf.setStrokeColor(colors.black)
        pdf.setLineWidth(0.5)
        pdf.line(50, start_y, 550, start_y)
        start_y -= 30  # Add space after the line

    # Footer
    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(50, 50, "Generated by Morris Sheetmetals - Workflow App")
    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer


def generate_quote_pdf(request, job_id):
    """
    Generate a PDF quote summary for a specific job.

    Args:
        request: The HTTP request object
        job_id: The ID of the job to generate the PDF for

    Returns:
        FileResponse: A PDF file response containing the quote summary

    Raises:
        Http404: If the job with the given ID does not exist
    """
    job = get_object_or_404(Job, pk=job_id)
    pdf_buffer = create_pdf(job)

    return FileResponse(
        pdf_buffer,
        as_attachment=False,
        filename=f"quote_summary_{job.name}.pdf",
        content_type="application/pdf",
    )


@csrf_exempt
def send_quote_email(request, job_id):
    try:
        job = get_object_or_404(Job, pk=job_id)
        logger.info(f"Processing quote email for job {job_id}")

        email = job.client.email if job.client and job.client.email else None

        if not email:
            logger.warning(f"No client email found for job {job_id}")
            messages.error(request, "Client email not found")
            return JsonResponse(
                {
                    "error": "Client email not found",
                    "messages": extract_messages(request),
                },
                status=400,
            )

        # Generate PDF
        try:
            pdf_buffer = create_pdf(job)
            pdf_content = pdf_buffer.getvalue()
            pdf_buffer.close()
            logger.debug(f"PDF generated successfully for job {job_id}")
        except Exception as e:
            logger.error(f"Error generating PDF for job {job_id}: {str(e)}")
            return JsonResponse(
                {"error": "Error generating PDF", "messages": str(e)}, status=500
            )

        # Determine e-mail type
        contact_only = request.GET.get("contact_only", "false").lower() == "true"

        subject = (
            f"Follow-up on Job #{job.name}"
            if contact_only
            else f"Quote Summary for {job.name}"
        )
        body = (
            f"Hello {job.client.name if job.client else 'Client'},\n\n"
            f"We are reaching out regarding Job #{job.name}.\n\n"
            f"Please let us know if you have any questions or require "
            f"further information.\n\n"
            f"Best regards,\nMorris Sheetmetals Works"
            if contact_only
            else f"Please find the attached quote summary for {job.name}."
        )

        mailto_url = f"mailto:{email}?subject={subject}&body={body}"

        logger.info(f"Email prepared successfully for job {job_id}")
        return JsonResponse(
            {
                "success": True,
                "mailto_url": mailto_url,
                "pdf_content": pdf_content.decode("latin-1"),  # Encode PDF for frontend
                "pdf_name": f"quote_summary_{job.name}.pdf",
            }
        )

    except Exception as e:
        logger.error(f"Unexpected error processing email for job {job_id}: {str(e)}")
        return JsonResponse(
            {"error": "Unexpected error occurred", "messages": str(e)}, status=500
        )
