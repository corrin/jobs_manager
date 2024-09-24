from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from workflow.api.xero.sync import debug_sync_invoice


def debug_sync_invoice_view(request, invoice_number):
    try:
        # Call your debug_sync_invoice function
        debug_sync_invoice(invoice_number)
        return JsonResponse({"status": "success", "message": f"Invoice {invoice_number} synced successfully."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def debug_sync_invoice_form(request):
    if request.method == "POST":
        invoice_number = request.POST.get("invoice_number")
        if not invoice_number:
            return JsonResponse({"status": "error", "message": "Please provide an invoice number."}, status=400)

        # Redirect to the correct view with the invoice number
        return redirect(f'{reverse("list_invoices")}?invoice_number={invoice_number}')

    return render(request, "workflow/debug_sync_invoice_form.html")