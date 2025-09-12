import os
import sys

import django

# Setup Django
sys.path.append("/home/corrin/src/jobs_manager")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from apps.workflow.api.xero.sync import clean_json, serialize_xero_object


class MockContact:
    def __init__(self) -> None:
        self.contact_id = "fd7ba987-0241-4fcb-adae-301155b9192f"


class MockBill:
    def __init__(self) -> None:
        self.contact = MockContact()


bill = MockBill()
print("Direct access:", bill.contact.contact_id)
serialized = serialize_xero_object(bill)
print("Serialized:", serialized)
cleaned = clean_json(serialized)
print("Cleaned:", cleaned)
