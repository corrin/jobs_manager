"""
Kanban Categorization Service

Service layer for managing the hierarchical kanban structure where:
- Main columns represent umbrella categories
- Sub-categories are shown as badges on job cards
- Real job status remains unchanged in the database
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class KanbanSubCategory:
    """Represents a sub-category within a kanban column"""

    status_key: str
    badge_label: str
    badge_color_class: str


@dataclass
class KanbanColumn:
    """Represents a main kanban column with its sub-categories"""

    column_id: str
    column_title: str
    sub_categories: List[KanbanSubCategory]
    color_theme: str


class KanbanCategorizationService:
    """
    Service for managing kanban categorization following SRP
    Centralizes all kanban categorization logic
    """

    # Define the hierarchical structure
    COLUMN_STRUCTURE = {
        "draft": KanbanColumn(
            column_id="draft",
            column_title="Draft",
            sub_categories=[KanbanSubCategory("quoting", "Quoting", "bg-yellow-500")],
            color_theme="yellow",
        ),
        "awaiting_approval": KanbanColumn(
            column_id="awaiting_approval",
            column_title="Awaiting Approval",
            sub_categories=[
                KanbanSubCategory("accepted_quote", "Quote Accepted", "bg-green-500")
            ],
            color_theme="green",
        ),
        "on_hold": KanbanColumn(
            column_id="on_hold",
            column_title="On Hold",
            sub_categories=[
                KanbanSubCategory(
                    "awaiting_materials", "Awaiting Materials", "bg-orange-500"
                ),
                KanbanSubCategory("awaiting_staff", "Awaiting Staff", "bg-purple-500"),
                KanbanSubCategory(
                    "awaiting_site_availability", "Awaiting Site", "bg-indigo-500"
                ),
                KanbanSubCategory("on_hold", "Other Hold", "bg-gray-500"),
            ],
            color_theme="orange",
        ),
        "in_progress": KanbanColumn(
            column_id="in_progress",
            column_title="In Progress",
            sub_categories=[
                KanbanSubCategory("in_progress", "Active Work", "bg-blue-500")
                # Note: 'special' is filtered out and not shown in kanban
            ],
            color_theme="blue",
        ),
        "recently_completed": KanbanColumn(
            column_id="recently_completed",
            column_title="Recently Completed",
            sub_categories=[
                KanbanSubCategory(
                    "recently_completed", "Just Finished", "bg-emerald-500"
                )
            ],
            color_theme="emerald",
        ),
        "archived": KanbanColumn(
            column_id="archived",
            column_title="Archived",
            sub_categories=[
                KanbanSubCategory("completed", "Completed & Paid", "bg-slate-500"),
                KanbanSubCategory("rejected", "Rejected", "bg-red-500"),
            ],
            color_theme="slate",
        ),
    }

    # Status to column mapping for quick lookup
    # Note: 'special' is intentionally excluded (filtered from kanban)
    STATUS_TO_COLUMN_MAP = {
        "quoting": "draft",
        "accepted_quote": "awaiting_approval",
        "awaiting_materials": "on_hold",
        "awaiting_staff": "on_hold",
        "awaiting_site_availability": "on_hold",
        "in_progress": "in_progress",
        "recently_completed": "recently_completed",
        "completed": "archived",  # completed goes to archived now
        "rejected": "archived",
        "archived": "archived",
        "on_hold": "on_hold",  # Fallback for generic on_hold
        # 'special' is intentionally omitted - filtered from kanban
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
    def get_sub_category_for_status(cls, status: str) -> Optional[KanbanSubCategory]:
        """
        Get the sub-category information for a status

        Args:
            status: Job status key

        Returns:
            KanbanSubCategory object or None if not found
        """
        column_id = cls.get_column_for_status(status)
        column = cls.COLUMN_STRUCTURE.get(column_id)

        if not column:
            return None

        # Find the sub-category that matches this status
        for sub_cat in column.sub_categories:
            if sub_cat.status_key == status:
                return sub_cat

        return None

    @classmethod
    def get_all_columns(cls) -> List[KanbanColumn]:
        """Get all kanban columns in display order"""
        return [
            cls.COLUMN_STRUCTURE["draft"],
            cls.COLUMN_STRUCTURE["awaiting_approval"],
            cls.COLUMN_STRUCTURE["on_hold"],
            cls.COLUMN_STRUCTURE["in_progress"],
            cls.COLUMN_STRUCTURE["recently_completed"],
            cls.COLUMN_STRUCTURE["archived"],
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
        valid_statuses = {sub_cat.status_key for sub_cat in column.sub_categories}

        return [job for job in jobs if getattr(job, "status", None) in valid_statuses]

    @classmethod
    def get_badge_info(cls, status: str) -> Dict[str, str]:
        """
        Get badge display information for a status

        Args:
            status: Job status key

        Returns:
            Dict with 'label' and 'color_class' keys
        """
        sub_category = cls.get_sub_category_for_status(status)

        if sub_category:
            return {
                "label": sub_category.badge_label,
                "color_class": sub_category.badge_color_class,
            }

        # Fallback for unknown statuses
        return {"label": status.replace("_", " ").title(), "color_class": "bg-gray-400"}
