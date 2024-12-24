from django.contrib.messages import get_messages


def extract_messages(request):
    """
    Extracts messages from the request object and returns them as a list of dictionaries.
    Each dictionary contains the message level tag and the message text.

    Args:
        request: The HTTP request object containing the messages

    Returns:
        list: A list of dictionaries, where each dictionary has:
            - level (str): The message level tag (e.g. 'info', 'error')
            - message (str): The message text
   """
   
    return [
        {"level": message.level_tag, "message": message.message}
        for message in get_messages(request)
    ]


def get_rate_type_label(multiplier):
    """
    Converts a pay rate multiplier to its corresponding label.

    Args:
        multiplier (float or str): The pay rate multiplier value (0.0, 1.0, 1.5, or 2.0)

    Returns:
        str: The label corresponding to the multiplier:
            - 'Unpaid' for 0.0
            - 'Ord' (Ordinary) for 1.0 
            - 'Ovt' (Overtime) for 1.5
            - 'Dt' (Double Time) for 2.0
            - 'Ord' as default for any other value

    Examples:
        >>> get_rate_type_label(1.5)
        'Ovt'
        >>> get_rate_type_label(0.0) 
        'Unpaid'
    """

    rate_map = {
        0.0: 'Unpaid',
        1.0: 'Ord',
        1.5: 'Ovt',
        2.0: 'Dt'
    }
    
    return rate_map.get(float(multiplier), 'Ord')  # Default to 'Ord' if not found


def create_paid_absence_job():
    """
    Creates a job with a paid absence entry for the 'Paid Absence Client'.
    This function is intended to be run once during the application's setup or initialization, but it's here to be reviewed later.
    It checks if the client exists, and if not, creates it. Then, it creates a job for the client.
    """
    from workflow.models import Client, Job
    from decimal import Decimal
    from datetime import datetime

    # Create new client
    client = Client.objects.create(
        name="Paid Absence Client",
        email="paidabsenceclient@example.com", 
        phone="123456789",
        address="123 Main St",
        is_account_customer=False,
        xero_last_modified=datetime.now(),
        raw_json=None
    )

    print(f"Client '{client.name}' created successfully!")

    # Create job associated with client
    job = Job.objects.create(
        name="Paid Absence Job",
        client=client,
        order_number="00000",
        contact_person="System", 
        contact_phone="0000000000",
        description="Virtual Job for Paid Absence",
        material_gauge_quantity="",
        quote_acceptance_date=None,
        delivery_date=None,
        status="completed", # Should it be something else? Anyway, it can be changed later 
        job_is_valid=True,
        paid=False,
        charge_out_rate=Decimal("0.00")
    )

    print(f"Job '{job.name}' created successfully!")
    print(f"ID: {job.id}, Number: {job.job_number}")    
