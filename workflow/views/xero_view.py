from datetime import timedelta

from decimal import Decimal

import logging

import uuid

import traceback

import json

from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import TemplateView

from xero_python.accounting import AccountingApi
from xero_python.identity import IdentityApi
from xero_python.accounting.models import (
    Invoice as XeroInvoice,
    LineItem,
    LineAmountTypes,
    Contact,
)
from xero_python.exceptions import AccountingBadRequestException

from workflow.api.xero.sync import synchronise_xero_data
from workflow.api.xero.xero import (
    api_client,
    exchange_code_for_token,
    get_authentication_url,
    get_token,
    refresh_token,
    get_tenant_id,
)
from workflow.models import Job, Invoice, InvoiceLineItem

logger = logging.getLogger("xero")


# Xero Authentication (Step 1: Redirect user to Xero OAuth2 login)
def xero_authenticate(request: HttpRequest) -> HttpResponse:
    state = str(uuid.uuid4())
    request.session["oauth_state"] = state
    authorization_url = get_authentication_url(state)
    return redirect(authorization_url)


# OAuth callback
def xero_oauth_callback(request: HttpRequest) -> HttpResponse:
    code = request.GET.get("code")
    state = request.GET.get("state")
    session_state = request.session.get("oauth_state")

    result = exchange_code_for_token(code, state, session_state)

    if "error" in result:
        return render(
            request, "xero/error_xero_auth.html", {"error_message": result["error"]}
        )

    return redirect("refresh_xero_data")


# Refresh OAuth token and handle redirects
def refresh_xero_token(request: HttpRequest) -> HttpResponse:
    refreshed_token = refresh_token()

    if not refreshed_token:
        return redirect("xero_authenticate")

    return redirect("xero_get_contacts")


# Xero connection success view
def success_xero_connection(request: HttpRequest) -> HttpResponse:
    return render(request, "xero/success_xero_connection.html")


def refresh_xero_data(request):
    try:
        token = get_token()

        if not token:
            logger.info(
                "User is not authenticated with Xero, redirecting to authentication"
            )
            return redirect(
                "authenticate_xero"
            )  # Redirect to the Xero authentication path

        # If authenticated, proceed with syncing data
        synchronise_xero_data()
        logger.info("Xero data successfully refreshed")

    except Exception as e:
        if "token" in str(e).lower():  # Or check for the specific error code
            logger.error(f"Error while refreshing Xero data: {str(e)}")
            return redirect("authenticate_xero")
        else:
            logger.error(f"Error while refreshing Xero data: {str(e)}")
            traceback.print_exc()
            return render(
                request, "general/generic_error.html", {"error_message": str(e)}
            )

    # After successful sync, redirect to the home page or wherever appropriate
    return redirect("/")


def create_xero_invoice(request, job_id):
    try:
        job = Job.objects.get(id=job_id)

        if not job.client:
            raise ValueError("Job does not have a client")

        client = job.client
        if not client.validate_for_xero():
            raise ValueError("Client data is not valid for Xero")

        line_items_data = [
            {
                "description": "Total Time",
                "quantity": 1,
                "unit_price": job.latest_reality_pricing.total_time_cost or float("0.00"),
            },
            {
                "description": "Total Materials",
                "quantity": 1,
                "unit_price": job.latest_reality_pricing.total_material_cost or float("0.00"),
            },
            {
                "description": "Total Adjustments",
                "quantity": 1,
                "unit_price": job.latest_reality_pricing.total_adjustment_cost or float("0.00"),
            },
        ]

        xero_line_items = [
            LineItem(
                description=item["description"],
                quantity=item["quantity"],
                unit_amount=item["unit_price"],
                tax_type="NONE",
            )
            for item in line_items_data
        ]

        xero_tenant_id = get_tenant_id()
        xero_api = AccountingApi(api_client)

        xero_contact = Contact(contact_id=client.xero_contact_id)
        xero_invoice = XeroInvoice(
            type="ACCREC",
            contact=xero_contact,
            line_items=xero_line_items,
            date=timezone.now().date(),
            due_date=(timezone.now().date() + timedelta(days=30)),
            line_amount_types=LineAmountTypes.EXCLUSIVE,
        )

        invoice_payload = xero_invoice.to_dict()
        logger.debug(f"Invoice payload being sent to Xero: {json.dumps(invoice_payload, indent=4)}")

        xero_tenant_id = get_tenant_id()
        response = xero_api.create_invoices(xero_tenant_id, [invoice_payload])

        if response and response.invoices:
            xero_invoice_data = response.invoices[0]

            invoice = Invoice.objects.create(
                xero_id=xero_invoice_data.invoice_id,
                client=client,
                date=timezone.now().date(),
                due_date=(timezone.now().date() + timedelta(days=30)),
                status="Draft",
                total_excl_tax=Decimal(xero_invoice_data.total),
                tax=Decimal(xero_invoice_data.total_tax),
                total_incl_tax=Decimal(xero_invoice_data.total) + Decimal(xero_invoice_data.total_tax),
                amount_due=Decimal(xero_invoice_data.amount_due),
                xero_last_modified=timezone.now(),
                raw_json=response.to_dict(),
            )

            logger.info(f"Invoice {invoice.id} created successfully for job {job_id}")
            return JsonResponse({
                "success": True,
                "invoice_id": invoice.id,
                "xero_id": invoice.xero_id,
                "client": invoice.client.name,
                "total_excl_tax": str(invoice.total_excl_tax),
                "total_incl_tax": str(invoice.total_incl_tax),
            })

    except AccountingBadRequestException as e:
        logger.error(f"Error creating invoice in Xero: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Job.DoesNotExist:
        return JsonResponse({"success": False, "error": "Job not found."}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


class XeroIndexView(TemplateView):
    """Note this page is currently inaccessible.  We are using a dropdown menu instead.
    Kept as of 2025-01-07 in case we change our mind"""

    template_name = "xero_index.html"
