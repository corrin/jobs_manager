from apps.workflow.api.xero.sync import clean_raw_json, serialise_xero_object


class MockContact:
    def __init__(self):
        self.contact_id = "fd7ba987-0241-4fcb-adae-301155b9192f"


class MockBill:
    def __init__(self):
        self.contact = MockContact()


bill = MockBill()
print("Direct access:", bill.contact.contact_id)
serialized = serialise_xero_object(bill)
print("Serialized:", serialized)
cleaned = clean_raw_json(serialized)
print("Cleaned:", cleaned)
