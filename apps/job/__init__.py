# This file is autogenerated by update_init.py script

from .apps import JobConfig
from .enums import MetalType

# Conditional imports (only when Django is ready)
try:
    from django.apps import apps

    if apps.ready:
        from .diff import DiffResult, apply_diff, diff_costset
        from .helpers import (
            DecimalEncoder,
            decimal_to_float,
            get_company_defaults,
            get_job_folder_path,
        )
        from .mixins import JobLookupMixin, JobNumberLookupMixin
        from .scheduler_jobs import set_paid_flag_jobs
        from .utils import get_active_jobs, get_jobs_data
except (ImportError, RuntimeError):
    # Django not ready or circular import, skip conditional imports
    pass

# EXCLUDED IMPORTS - These contain problematic dependencies that cause circular imports
# Import these directly where needed using:
# from .admin import CostLineAdmin
# from .admin import CostLineInline
# from .admin import CostSetAdmin
#

__all__ = [
    "DecimalEncoder",
    "DiffResult",
    "JobConfig",
    "JobLookupMixin",
    "JobNumberLookupMixin",
    "MetalType",
    "apply_diff",
    "decimal_to_float",
    "diff_costset",
    "get_active_jobs",
    "get_company_defaults",
    "get_job_folder_path",
    "get_jobs_data",
    "set_paid_flag_jobs",
]
