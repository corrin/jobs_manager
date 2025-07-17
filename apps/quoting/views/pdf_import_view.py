import json
import logging
import os
import tempfile
from typing import Dict, List, Optional

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import TemplateView

from apps.client.models import Client
from apps.quoting.models import SupplierPriceList, SupplierProduct
from apps.quoting.services.ai_price_extraction import extract_price_data
from apps.quoting.services.pdf_data_validation import PDFDataValidationService
from apps.quoting.services.pdf_import_service import PDFImportService
from apps.quoting.services.product_parser import (
    create_mapping_record,
    populate_all_mappings_with_llm,
)

logger = logging.getLogger(__name__)


class PDFPriceListImportView(LoginRequiredMixin, TemplateView):
    """
    Enhanced view for uploading and processing supplier pricing PDFs with preview functionality.
    
    Workflow:
    1. Upload PDF file
    2. Extract data using AI
    3. Preview extracted data with editing capabilities
    4. Confirm and import to database
    """
    
    template_name = "quoting/pdf_price_list_import.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Import PDF Price List"
        context["uploaded_pricing"] = SupplierPriceList.objects.all().order_by(
            "-uploaded_at"
        )
        
        # Check if we have preview data in session
        if "preview_data" in self.request.session:
            context["preview_data"] = self.request.session["preview_data"]
            context["show_preview"] = True
        else:
            context["show_preview"] = False
            
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle different POST actions based on the action parameter."""
        action = request.POST.get("action", "upload")
        
        if action == "upload":
            return self._handle_upload(request)
        elif action == "preview":
            return self._handle_preview_update(request)
        elif action == "confirm":
            return self._handle_confirm_import(request)
        elif action == "cancel":
            return self._handle_cancel(request)
        else:
            messages.error(request, "Invalid action specified.")
            return self.get(request, *args, **kwargs)
    
    def _handle_upload(self, request):
        """Handle PDF file upload and extraction."""
        if "pdf_file" not in request.FILES:
            messages.error(request, "No PDF file was uploaded.")
            return self.get(request)
        
        uploaded_file = request.FILES["pdf_file"]
        
        # Validate file type
        if not uploaded_file.content_type == "application/pdf":
            messages.error(request, "Please upload a valid PDF file.")
            return self.get(request)
        
        logger.info(
            f"Processing PDF upload: {uploaded_file.name}, size: {uploaded_file.size} bytes"
        )
        
        # Save file temporarily
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
            ) as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
        except Exception as e:
            logger.error(f"Error saving temporary file: {e}")
            messages.error(request, "Error processing uploaded file.")
            return self.get(request)
        
        # Extract data using AI
        try:
            extracted_data, error = extract_price_data(temp_file_path, uploaded_file.content_type)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            if error:
                messages.error(request, f"Error extracting data: {error}")
                return self.get(request)
            
            # Validate extracted data
            validation_service = PDFDataValidationService()
            is_valid, errors, warnings = validation_service.validate_extracted_data(extracted_data)
            
            if not is_valid:
                error_msg = "Data validation failed: " + "; ".join(errors)
                messages.error(request, error_msg)
                return self.get(request)
            
            # Show warnings if any
            if warnings:
                warning_msg = "Data validation warnings: " + "; ".join(warnings)
                messages.warning(request, warning_msg)
            
            # Sanitize the extracted items
            raw_items = extracted_data.get("items", [])
            sanitized_items = validation_service.sanitize_product_data(raw_items)
            
            # Check for duplicates
            import_service = PDFImportService()
            supplier_name = extracted_data.get("supplier", {}).get("name", "Morris SM")
            duplicate_analysis = import_service.handle_duplicates(sanitized_items, supplier_name, "skip")
            
            # Store extracted data in session for preview
            preview_data = {
                "filename": uploaded_file.name,
                "supplier_name": supplier_name,
                "items": sanitized_items,
                "parsing_stats": extracted_data.get("parsing_stats", {}),
                "total_items": len(sanitized_items),
                "validation_summary": validation_service.get_validation_summary(),
                "duplicate_analysis": duplicate_analysis
            }
            
            request.session["preview_data"] = preview_data
            request.session.modified = True
            
            messages.success(
                request, 
                f"Successfully extracted {preview_data['total_items']} products. Please review the data below."
            )
            
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            logger.exception(f"Error during PDF extraction: {e}")
            messages.error(request, f"Error processing PDF: {str(e)}")
        
        return self.get(request)
    
    def _handle_preview_update(self, request):
        """Handle updates to preview data from the frontend."""
        try:
            # Get updated data from POST request
            updated_items = json.loads(request.POST.get("items", "[]"))
            
            if "preview_data" in request.session:
                preview_data = request.session["preview_data"]
                preview_data["items"] = updated_items
                request.session["preview_data"] = preview_data
                request.session.modified = True
                
                return JsonResponse({"success": True, "message": "Preview data updated"})
            else:
                return JsonResponse({"success": False, "error": "No preview data found"})
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing preview update data: {e}")
            return JsonResponse({"success": False, "error": "Invalid data format"})
        except Exception as e:
            logger.exception(f"Error updating preview data: {e}")
            return JsonResponse({"success": False, "error": str(e)})
    
    def _handle_confirm_import(self, request):
        """Handle final import confirmation and database insertion."""
        if "preview_data" not in request.session:
            messages.error(request, "No preview data found. Please upload a file first.")
            return self.get(request)
        
        preview_data = request.session["preview_data"]
        supplier_name = preview_data["supplier_name"]
        items_data = preview_data["items"]
        filename = preview_data["filename"]
        
        # Get duplicate handling strategy from form
        duplicate_strategy = request.POST.get("duplicate_strategy", "skip")
        
        if not items_data:
            messages.error(request, "No products to import.")
            return self.get(request)
        
        logger.info(f"Starting import for supplier '{supplier_name}' with {len(items_data)} items using duplicate strategy: {duplicate_strategy}")
        
        try:
            # Use the import service for atomic operations
            import_service = PDFImportService()
            
            with transaction.atomic():
                # Create or get supplier
                supplier, created = import_service.create_or_get_supplier(supplier_name)
                
                # Create price list
                price_list = import_service.create_price_list(supplier, filename)
                
                # Import products with duplicate handling
                import_stats = import_service.import_products(items_data, supplier, price_list, duplicate_strategy)
                
                # Process LLM mappings
                populate_all_mappings_with_llm()
                
                # Clear session data
                del request.session["preview_data"]
                request.session.modified = True
                
                # Create success message with detailed stats
                success_msg = (
                    f"Import completed for {supplier_name}: "
                    f"{import_stats['imported']} imported, "
                    f"{import_stats['updated']} updated, "
                    f"{import_stats['skipped']} skipped"
                )
                if import_stats['failed'] > 0:
                    success_msg += f", {import_stats['failed']} failed"
                
                messages.success(request, success_msg)
                
        except Exception as e:
            logger.exception(f"Error during import: {e}")
            messages.error(request, f"Import failed: {str(e)}")
        
        return self.get(request)
    
    def _handle_cancel(self, request):
        """Handle cancellation of import process."""
        if "preview_data" in request.session:
            del request.session["preview_data"]
            request.session.modified = True
        
        messages.info(request, "Import cancelled.")
        return self.get(request)
    
