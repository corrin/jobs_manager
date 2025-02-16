import logging

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django_tables2 import SingleTableView

from xero_python.accounting import AccountingApi
from workflow.api.xero.reprocess_xero import set_client_fields
from workflow.api.xero.sync import (
    single_sync_client,
    sync_client_to_xero,
    serialise_xero_object,
    sync_clients,
    sync_xero_clients_only
)
from workflow.api.xero.xero import get_valid_token, api_client, get_tenant_id
from workflow.forms import ClientForm
from workflow.models import Client

# from workflow.tables import ClientTable

logger = logging.getLogger(__name__)


class ClientListView(SingleTableView):
    model = Client
    template_name = "clients/list_clients.html"


class ClientUpdateView(UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/update_client.html"
    success_url = reverse_lazy("list_clients")

    def form_valid(self, form):
        response = super().form_valid(form)

        # Simple token check before attempting sync
        token = get_valid_token()
        if not token:
            messages.warning(self.request, "Xero authentication required.")
            return redirect("authenticate_xero")

        try:
            sync_client_to_xero(self.object)
            messages.success(self.request, "Client synced to Xero successfully")
        except Exception as e:
            messages.error(self.request, "Failed to sync to Xero")
            return render(
                self.request,
                "general/generic_error.html",
                {"error_message": f"Failed to sync client to Xero: {str(e)}"},
            )

        return response


def ClientSearch(request):
    query = request.GET.get("q", "")
    if query and len(query) >= 3:  # Only search when the query is 3+ characters
        clients = Client.objects.filter(Q(name__icontains=query))[:10]
        results = [{
            "id": client.id,
            "name": client.name,
            "email": client.email or "",
            "phone": client.phone or "",
            "address": client.address or "",
            "is_account_customer": client.is_account_customer,
            "last_invoice_date": client.get_last_invoice_date().strftime('%d/%m/%Y') if client.get_last_invoice_date() else "",
            "total_spend": f"${client.get_total_spend():,.2f}"
        } for client in clients]
    else:
        results = []

    return JsonResponse({"results": results})


def all_clients(request):
    """
    API endpoint to return all clients as JSON for AJAX table population.
    """
    clients = Client.objects.values(
        "id", "name", "email", "phone", "address", "is_account_customer"
    )
    return JsonResponse(list(clients), safe=False)


def AddClient(request):
    # Check for valid Xero token first
    token = get_valid_token()
    if not token:
        messages.add_message(
            request,
            messages.WARNING,
            "Xero authentication required",
            extra_tags='warning'
        )
        # Store the current URL with query parameters to return to after auth
        return_url = f"{request.path}?{request.GET.urlencode()}" if request.GET else request.path
        return redirect(f"{reverse_lazy('authenticate_xero')}?next={return_url}")
    if request.method == "GET":
        # Sync clients from Xero before displaying the form
        # Otherwise we try and create clients only to discover they already exist too much
        sync_xero_clients_only()
        
        name = request.GET.get("name", "")
        form = ClientForm(initial={"name": name}) if name else ClientForm()
        return render(request, "clients/add_client.html", {"form": form})

    elif request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            # Create in Xero first
            accounting_api = AccountingApi(api_client)
            xero_tenant_id = get_tenant_id()
            
            try:
                # Log the form data
                logger.debug("Form cleaned data: %s", form.cleaned_data)
                
                # Check if contact already exists
                existing_contacts = accounting_api.get_contacts(
                    xero_tenant_id,
                    where=f'Name="{form.cleaned_data["name"]}"'
                )
                
                if existing_contacts and existing_contacts.contacts:
                    # Use existing contact
                    logger.info("Found existing contact with name: %s", form.cleaned_data["name"])
                    response = existing_contacts
                    messages.info(request, "Client already exists in Xero - using existing record")
                else:
                    # Create new contact in Xero
                    contact_data = {
                        "name": form.cleaned_data["name"],
                        "emailAddress": form.cleaned_data["email"] or "",
                        "phones": [{"phoneType": "DEFAULT", "phoneNumber": form.cleaned_data["phone"] or ""}],
                        "addresses": [{"addressType": "STREET", "addressLine1": form.cleaned_data["address"] or ""}],
                        "isCustomer": form.cleaned_data["is_account_customer"]
                    }
                    logger.debug("Xero contact data: %s", contact_data)
                    
                    response = accounting_api.create_contacts(
                        xero_tenant_id,
                        contacts={
                            "contacts": [contact_data]
                        }
                    )
                
                # Log and validate response
                logger.debug("Xero API response: %s", response)
                
                if not response:
                    raise ValueError("No response received from Xero")
                    
                if not hasattr(response, 'contacts') or not response.contacts:
                    raise ValueError("No contact data in Xero response")
                    
                if len(response.contacts) != 1:
                    raise ValueError(f"Expected 1 contact in response, got {len(response.contacts)}")
                
                # Use sync_clients to create local client from Xero data
                sync_clients(response.contacts)
                messages.success(request, "Client created successfully")
                return redirect("list_clients")
                
            except Exception as e:
                error_msg = f"Failed to create client in Xero: {str(e)}"
                logger.error(error_msg, exc_info=True)
                messages.add_message(
                    request,
                    messages.ERROR,
                    error_msg,
                    extra_tags='danger'  # Bootstrap uses 'danger' for red alerts
                )
                return render(
                    request,
                    "clients/add_client.html",
                    {"form": form}
                )
        else:
            return render(request, "clients/add_client.html", {"form": form})
