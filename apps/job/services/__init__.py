# This file is autogenerated by update_init.py script

# Conditional imports (only when Django is ready)
try:
    from django.apps import apps

    if apps.ready:
        from .file_service import (
            create_thumbnail,
            get_thumbnail_folder,
            sync_job_folder,
        )
        from .gemini_chat_service import GeminiChatService
        from .import_quote_service import (
            QuoteImportError,
            QuoteImportResult,
            import_quote_from_drafts,
            import_quote_from_file,
            preview_quote_import,
            preview_quote_import_from_drafts,
            serialize_draft_lines,
            serialize_validation_report,
        )
        from .job_rest_service import JobRestService
        from .job_service import (
            JobStaffService,
            archive_complete_jobs,
            get_paid_complete_jobs,
        )
        from .kanban_categorization_service import (
            KanbanCategorizationService,
            KanbanColumn,
        )
        from .kanban_service import KanbanService
        from .mcp_chat_service import MCPChatService
        from .month_end_service import MonthEndService
        from .paid_flag_service import PaidFlagResult, PaidFlagService
        from .workshop_pdf_service import (
            add_job_details_table,
            add_logo,
            add_materials_table,
            add_title,
            convert_html_to_reportlab,
            create_image_document,
            create_main_document,
            create_workshop_pdf,
            get_image_dimensions,
            get_pdf_file_paths,
            merge_pdfs,
            process_attachments,
            wait_until_file_ready,
        )
except (ImportError, RuntimeError):
    # Django not ready or circular import, skip conditional imports
    pass

__all__ = [
    "GeminiChatService",
    "JobRestService",
    "JobStaffService",
    "KanbanCategorizationService",
    "KanbanColumn",
    "KanbanService",
    "MCPChatService",
    "MonthEndService",
    "PaidFlagResult",
    "PaidFlagService",
    "QuoteImportError",
    "QuoteImportResult",
    "add_job_details_table",
    "add_logo",
    "add_materials_table",
    "add_title",
    "archive_complete_jobs",
    "convert_html_to_reportlab",
    "create_image_document",
    "create_main_document",
    "create_thumbnail",
    "create_workshop_pdf",
    "get_image_dimensions",
    "get_paid_complete_jobs",
    "get_pdf_file_paths",
    "get_thumbnail_folder",
    "import_quote_from_drafts",
    "import_quote_from_file",
    "merge_pdfs",
    "preview_quote_import",
    "preview_quote_import_from_drafts",
    "process_attachments",
    "serialize_draft_lines",
    "serialize_validation_report",
    "sync_job_folder",
    "wait_until_file_ready",
]
