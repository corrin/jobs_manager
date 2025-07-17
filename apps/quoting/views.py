from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from apps.workflow.authentication import service_api_key_required

class UploadSupplierPricingView(TemplateView):
    template_name = "purchasing/upload_supplier_pricing.html"

class UploadPriceListView(TemplateView):
    template_name = "quoting/upload_price_list.html"

@require_http_methods(["POST"])
def extract_supplier_price_list_data_view(request):
    return JsonResponse({"success": False, "error": "Service temporarily disabled"})

@service_api_key_required
@require_http_methods(["GET"])
def search_stock_api(request):
    return JsonResponse({"stock_items": []})

@service_api_key_required
@require_http_methods(["GET"])
def search_supplier_prices_api(request):
    return JsonResponse({"supplier_prices": []})

@service_api_key_required
@require_http_methods(["GET"])
def job_context_api(request, job_id):
    return JsonResponse({"error": "Service temporarily disabled"}, status=500)