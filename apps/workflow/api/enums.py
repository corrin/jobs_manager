import importlib
import inspect
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def get_enum_choices(request, enum_name):
    """
    API endpoint to get enum choices.
    Returns the choices for the specified enum as a JSON object.

    Args:
        request: The HTTP request
        enum_name: The name of the enum to get choices for (e.g., 'MetalType')

    Returns:
        JsonResponse with the enum choices
    """
    try:
        # First check the job enums module
        try:
            enums_module = importlib.import_module("apps.job.enums")

            if hasattr(enums_module, enum_name):
                enum_class = getattr(enums_module, enum_name)

                if hasattr(enum_class, "choices"):
                    choices = [
                        {"value": value, "display_name": display_name}
                        for value, display_name in enum_class.choices
                    ]
                    return JsonResponse({"choices": choices})
        except (ImportError, AttributeError):
            # Fall back to workflow enums
            pass

        # Fall back to workflow.enums if not found in job.enums
        enums_module = importlib.import_module("apps.workflow.enums")

        if hasattr(enums_module, enum_name):
            enum_class = getattr(enums_module, enum_name)

            if hasattr(enum_class, "choices"):
                choices = [
                    {"value": value, "display_name": display_name}
                    for value, display_name in enum_class.choices
                ]
                return JsonResponse({"choices": choices})
            else:
                return JsonResponse(
                    {
                        "error": f'"{enum_name}" does not appear to be a valid Django Choices enum'
                    },
                    status=400,
                )
        else:
            # List available enums from both modules
            job_enums_module = importlib.import_module("job.enums")
            workflow_enums_module = importlib.import_module("workflow.enums")

            job_enums = [
                name
                for name, obj in inspect.getmembers(job_enums_module)
                if inspect.isclass(obj) and hasattr(obj, "choices")
            ]

            workflow_enums = [
                name
                for name, obj in inspect.getmembers(workflow_enums_module)
                if inspect.isclass(obj) and hasattr(obj, "choices")
            ]

            return JsonResponse(
                {
                    "error": f'Enum "{enum_name}" not found',
                    "available_enums": {"job": job_enums, "workflow": workflow_enums},
                },
                status=404,
            )

    except Exception as e:
        logger.exception(f"Unexpected error getting enum choices: {e}")
        return JsonResponse(
            {"error": "An unexpected server error occurred."}, status=500
        )
