"""
Kanban Categorization Service

Service layer for managing simplified kanban structure:
- 6 main columns with 1:1 status mapping (no sub-columns)
- Column = Status (simplified approach as requested by Cindy)
- Hidden statuses: special, rejected, archived (maintained but not shown)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class KanbanColumn:
    """Represents a kanban column - simplified structure without sub-categories"""

    column_id: str
    column_title: str
    status_key: str  # Direct 1:1 mapping to job status
    color_theme: str
    badge_color_class: str


class KanbanCategorizationService:
    """
    Service for managing simplified kanban categorization following SRP
    Centralizes all kanban categorization logic
    New approach: 1:1 mapping between column and status (no sub-columns)
    """

    # Define the simplified column structure (column = status)
    COLUMN_STRUCTURE = {
        "draft": KanbanColumn(
            column_id="draft",
            column_title="Draft",
            status_key="draft",
            color_theme="yellow",
            badge_color_class="bg-yellow-500",
        ),
        "awaiting_approval": KanbanColumn(
            column_id="awaiting_approval",
            column_title="Awaiting Approval",
            status_key="awaiting_approval",
            color_theme="orange",
            badge_color_class="bg-orange-500",
        ),
        "approved": KanbanColumn(
            column_id="approved",
            column_title="Approved",
            status_key="approved",
            color_theme="green",
            badge_color_class="bg-green-500",
        ),
        "in_progress": KanbanColumn(
            column_id="in_progress",
            column_title="In Progress",
            status_key="in_progress",
            color_theme="blue",
            badge_color_class="bg-blue-500",
        ),
        "unusual": KanbanColumn(
            column_id="unusual",
            column_title="Unusual",
            status_key="unusual",
            color_theme="purple",
            badge_color_class="bg-purple-500",
        ),
        "recently_completed": KanbanColumn(
            column_id="recently_completed",
            column_title="Recently Completed",
            status_key="recently_completed",
            color_theme="emerald",
            badge_color_class="bg-emerald-500",
        ),
    }

    # Status to column mapping for quick lookup - simplified 1:1 mapping
    STATUS_TO_COLUMN_MAP = {
        # New status structure - 1:1 mapping (column = status)
        "draft": "draft",
        "awaiting_approval": "awaiting_approval",
        "approved": "approved",
        "in_progress": "in_progress",
        "unusual": "unusual",
        "recently_completed": "recently_completed",
        # Legacy status mappings for backward compatibility (will be migrated)
        "quoting": "awaiting_approval",  # Legacy: map to awaiting_approval
        "accepted_quote": "approved",  # Legacy: map to approved
        "awaiting_materials": "in_progress",  # Legacy: map to in_progress
        "awaiting_staff": "in_progress",  # Legacy: map to in_progress
        "awaiting_site_availability": "in_progress",  # Legacy: map to in_progress
        "on_hold": "unusual",  # Legacy: map to unusual
        "completed": "recently_completed",  # Legacy: map to recently_completed
        # Hidden statuses (not shown on kanban): special, rejected, archived
    }

    @classmethod
    def get_column_for_status(cls, status: str) -> str:
        """
        Get the kanban column for a given job status

        Args:
            status: Job status key

        Returns:
            Column ID for the kanban board
        """
        return cls.STATUS_TO_COLUMN_MAP.get(status, "draft")

    @classmethod
    def get_column_info_for_status(cls, status: str) -> Optional[KanbanColumn]:
        """
        Get the column information for a status

        Args:
            status: Job status key

        Returns:
            KanbanColumn object or None if not found
        """
        column_id = cls.get_column_for_status(status)
        return cls.COLUMN_STRUCTURE.get(column_id)

    @classmethod
    def get_all_columns(cls) -> List[KanbanColumn]:
        """Get all kanban columns in display order"""
        return [
            cls.COLUMN_STRUCTURE["draft"],
            cls.COLUMN_STRUCTURE["awaiting_approval"],
            cls.COLUMN_STRUCTURE["approved"],
            cls.COLUMN_STRUCTURE["in_progress"],
            cls.COLUMN_STRUCTURE["unusual"],
            cls.COLUMN_STRUCTURE["recently_completed"],
        ]

    @classmethod
    def get_column_by_id(cls, column_id: str) -> Optional[KanbanColumn]:
        """Get a specific column by its ID"""
        return cls.COLUMN_STRUCTURE.get(column_id)

    @classmethod
    def get_jobs_for_column(cls, jobs: List, column_id: str) -> List:
        """
        Filter jobs that belong to a specific column

        Args:
            jobs: List of job objects with 'status' attribute
            column_id: The column ID to filter by

        Returns:
            List of jobs that belong to this column
        """
        if column_id not in cls.COLUMN_STRUCTURE:
            return []

        column = cls.COLUMN_STRUCTURE[column_id]
        # With simplified structure, only jobs with exact status match belong to column
        return [
            job for job in jobs if getattr(job, "status", None) == column.status_key
        ]

    @classmethod
    def get_badge_info(cls, status: str) -> Dict[str, str]:
        """
        Get badge display information for a status

        Args:
            status: Job status key

        Returns:
            Dict with 'label' and 'color_class' keys
        """
        column_info = cls.get_column_info_for_status(status)

        if column_info:
            return {
                "label": column_info.column_title,
                "color_class": column_info.badge_color_class,
            }

        # Fallback for unknown statuses
        return {"label": status.replace("_", " ").title(), "color_class": "bg-gray-400"}

    @classmethod
    def is_status_hidden_from_kanban(cls, status: str) -> bool:
        """
        Check if a status should be hidden from kanban display

        Args:
            status: Job status key

        Returns:
            True if status should be hidden from kanban
        """
        hidden_statuses = {"special", "rejected", "archived"}
        return status in hidden_statuses

    @classmethod
    def get_visible_jobs_for_kanban(cls, jobs: List) -> List:
        """
        Filter jobs that should be visible on kanban (exclude hidden statuses)

        Args:
            jobs: List of job objects with 'status' attribute

        Returns:
            List of jobs that should be shown on kanban
        """
        return [
            job
            for job in jobs
            if not cls.is_status_hidden_from_kanban(getattr(job, "status", ""))
        ]
