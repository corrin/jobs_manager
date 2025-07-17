from .pdf_import_view import PDFPriceListImportView

# Import from the main views.py file in the parent directory
import importlib.util
import os

# Get the path to the views.py file in the parent directory
views_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'views.py')

# Load the views.py module
spec = importlib.util.spec_from_file_location("views_module", views_py_path)
views_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(views_module)

# Import all classes and functions from views.py
UploadSupplierPricingView = views_module.UploadSupplierPricingView
UploadPriceListView = views_module.UploadPriceListView
extract_supplier_price_list_data_view = views_module.extract_supplier_price_list_data_view
search_stock_api = views_module.search_stock_api
search_supplier_prices_api = views_module.search_supplier_prices_api
job_context_api = views_module.job_context_api

__all__ = ["PDFPriceListImportView", "UploadSupplierPricingView", "UploadPriceListView", 
           "extract_supplier_price_list_data_view", "search_stock_api", 
           "search_supplier_prices_api", "job_context_api"]