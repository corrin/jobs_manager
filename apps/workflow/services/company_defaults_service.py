from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound

from apps.workflow.models.company_defaults import CompanyDefaults


def get_company_defaults():
    try:
        return CompanyDefaults.get_instance()
    except ObjectDoesNotExist:
        raise NotFound("CompanyDefaults instance does not exist.")
