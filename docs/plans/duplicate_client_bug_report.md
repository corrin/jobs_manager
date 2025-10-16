Note when reading this bug report.  Be aware that Xero is the owner of Clients but we are the owner of ClientContacts

Xero is a SOURCE for client contacts.  If Xero adds or modifies a contact to a clent then we should upset  a ClientClient
But... if we create or update a clientcontact then we do not send that to Xero.

This makes it quite possible for us to create one, then Xero creates the same one, then we get that update from Xero and we need to match
and make that an update rather than a create.

It's quite important we don't sync our clientcontact back to Xero.  Xero's data model only supports a 1:1 while ours is 1:many


 ⎿ ================================================================================
    DEEP SYNC BUG REPORT
    Generated: 2025-10-15T09:18:35.805183
    ================================================================================

    ## 1. ERROR DETAILS
    ----------------------------------------
    Command that fails:
      python manage.py start_xero_sync --entity contacts --deep-sync --days-back 9

    Error message:
      apps.client.models.ClientContact.MultipleObjectsReturned:
      get() returned more than one ClientContact -- it returned more than 20!

    Error location:
      File: apps/workflow/api/xero/reprocess_xero.py
      Line: 282
      Code: ClientContact.objects.update_or_create(
              client=client, name=name, defaults={'email': email})

    ## 2. DUPLICATE CLIENTCONTACT ANALYSIS
    ----------------------------------------
    Found 65 client/name combinations with duplicates

    Top 10 worst offenders:

    1. Client: Vulcan Steel Limited (ID: be54c909-2579-468c-a141-1ce366f1cd0c)
       Contact Name: ''
       Duplicate Count: 76
         - Contact ID: cdd596ee-c73d-41a1-a14d-01e8dd9812c1, Email: adminteam@vulcansteel.co.nz
         - Contact ID: 10d18783-e3ff-4c71-a9a5-02dbcee9dcbe, Email: adminteam@vulcansteel.co.nz
         - Contact ID: 4ee1d120-e031-412f-a62e-03466ad6c5fd, Email: adminteam@vulcansteel.co.nz
         - Contact ID: 8f339143-8f20-4b7a-974e-065b73d6018e, Email: adminteam@vulcansteel.co.nz
         - Contact ID: 448833cf-a794-4a05-a396-065dd6bacccc, Email: adminteam@vulcansteel.co.nz

    2. Client: Coregas NZ Ltd/Supagas 2009 Limited (ID: cf814af4-2ea9-405a-aa91-51752326a83a)
       Contact Name: ''
       Duplicate Count: 42
         - Contact ID: 2e99a751-85c3-4c1e-94e8-08e2d3c46ccc, Email: enquiries@coregas.co.nz
         - Contact ID: 2adf3885-a4b0-4abb-b9fd-0b2cb03bea94, Email: Karen.Nair@coregas.co.nz
         - Contact ID: fd670031-212f-44e7-997e-12db755f39e7, Email: Karen.Nair@coregas.co.nz
         - Contact ID: 13ac5c8e-14f4-4739-898a-1ffa5b14a3ad, Email: Karen.Nair@coregas.co.nz
         - Contact ID: f690e5a4-7b9b-4651-a22e-208f9f793111, Email: enquiries@coregas.co.nz

    3. Client: Power Tool Centre (ID: 7be28217-4dc1-4412-bdb4-3257ecda64c6)
       Contact Name: 'Email'
       Duplicate Count: 29
         - Contact ID: 02a85569-be4b-40ab-a7fe-0e05b4efbd03, Email: optc@xtra.co.nz
         - Contact ID: c48a84ef-d0b5-4827-9a90-1051b4db72c9, Email: optc@xtra.co.nz
         - Contact ID: a9c93c87-946a-4661-8c13-15963c7ca2f3, Email: optc@xtra.co.nz
         - Contact ID: 96ecc6ee-741c-4b25-9d28-1ea7b01896eb, Email: optc@xtra.co.nz
         - Contact ID: 96ba8f75-1fd9-4ca7-9db7-2905bcb060b1, Email: optc@xtra.co.nz

    4. Client: Galvanising Services 2018 Limited (ID: 13b17302-270b-4cdb-b4d4-a6624fbf108b)
       Contact Name: 'old email'
       Duplicate Count: 23
         - Contact ID: 4cbccf29-3d50-4303-847d-11a2d7e336e7, Email: gsl@vodafone.co.nz
         - Contact ID: ee8677d6-0429-4c72-ba3d-133ff60c8dba, Email: gsl@vodafone.co.nz
         - Contact ID: ade75770-d4a5-4588-90a1-353fd7ed7400, Email: gsl@vodafone.co.nz
         - Contact ID: 8d0e7303-ad45-4908-8ee6-4cd3811049fd, Email: gsl@vodafone.co.nz
         - Contact ID: b05219f9-1125-4502-8e4c-5bcabf530ab1, Email: gsl@vodafone.co.nz

    5. Client: Fluid and General Ltd (ID: d1d20d2d-5638-4feb-ba4b-c28a5c5d0bd8)
       Contact Name: 'Sales'
       Duplicate Count: 12
         - Contact ID: f37d2f6a-7fe3-4265-b8b1-154a94fae335, Email: sales@fluidandgeneral.co.nz
         - Contact ID: 6452914c-59d8-4565-87ee-2c1bb0703764, Email: sales@fluidandgeneral.co.nz
         - Contact ID: 68c20b15-013d-4faf-a987-2df2cd8049c6, Email: sales@fluidandgeneral.co.nz
         - Contact ID: 7c6e6f69-9aa4-4a4c-8ebf-36232abff7cc, Email: sales@fluidandgeneral.co.nz
         - Contact ID: 9b3dc814-8985-4b75-8d1a-405de03a9590, Email: sales@fluidandgeneral.co.nz

    6. Client: PPS Industries Limited (ID: abea2e4a-ad0e-4c5f-8d81-69517ae4c1a3)
       Contact Name: ''
       Duplicate Count: 9
         - Contact ID: 393d420d-7952-49b2-a069-0a61ea871d58, Email: ttischendorf@ppsindustries.co.nz
         - Contact ID: 99d69ebc-f6bf-4105-ae8a-1a78ba549d18, Email: ttischendorf@ppsindustries.co.nz
         - Contact ID: bfaba6ec-6aba-444f-b0d9-20af0a8b2d5c, Email: ttischendorf@ppsindustries.co.nz
         - Contact ID: 6899adf8-7e04-4513-8695-8a2bd12959d3, Email: ttischendorf@ppsindustries.co.nz
         - Contact ID: 9c98f007-aa8d-4576-93c9-8c85e5cc04bb, Email: ttischendorf@ppsindustries.co.nz

    7. Client: Sitecare Ltd (ID: 71e5089a-98f5-43a0-9dc1-31380bf63a7f)
       Contact Name: 'Accounts - no'
       Duplicate Count: 8
         - Contact ID: df55ff62-3043-49f0-aa86-0bcd03183106, Email: accountspayable@eclgroup.co.nz
         - Contact ID: 3eefebb7-c45d-447e-99c4-236a229bfe10, Email: accountspayable@eclgroup.co.nz
         - Contact ID: 8f7ea510-d2c5-49fa-bb0d-2d6fe2c7bfae, Email: accountspayable@eclgroup.co.nz
         - Contact ID: d027c82a-1767-4ef4-8405-56297ec939eb, Email: accountspayable@eclgroup.co.nz
         - Contact ID: f48b522c-670e-48d1-8032-5e848ad89fd6, Email: accountspayable@eclgroup.co.nz

    8. Client: Sitecare Ltd (ID: 71e5089a-98f5-43a0-9dc1-31380bf63a7f)
       Contact Name: 'not this address Not part of ECL now'
       Duplicate Count: 8
         - Contact ID: ddf013ff-951f-41d5-a40e-175310670041, Email: sitecare.accounts@eclgroup.co.nz
         - Contact ID: dbd029b2-9000-4c7b-9c64-26374f941969, Email: sitecare.accounts@eclgroup.co.nz
         - Contact ID: bbccaac2-0490-4627-9303-2f6601f18a95, Email: sitecare.accounts@eclgroup.co.nz
         - Contact ID: a2af4b45-ef6e-4c6b-b80e-476091554d56, Email: sitecare.accounts@eclgroup.co.nz
         - Contact ID: 727a8c53-2a9e-43ea-8b3c-7e67f83b32d3, Email: sitecare.accounts@eclgroup.co.nz

    9. Client: Medifab (ID: 12cdc600-e269-4700-bc56-08d415a6d431)
       Contact Name: 'Angus'
       Duplicate Count: 7
         - Contact ID: d9932a32-bc55-4b30-913c-070550ec4e34, Email: angus.filleul@medifab.com
         - Contact ID: 86be1c28-a0e8-40b3-bfb5-271b240dcc25, Email: angus.filleul@medifab.com
         - Contact ID: 00e12d80-2408-4751-8dd9-4bc50b3bbaea, Email: angus.filleul@medifab.com
         - Contact ID: ec83e3b8-c6d4-4cf7-bad5-5dfb888dc64a, Email: angus.filleul@medifab.com
         - Contact ID: 4a3f1e61-c447-4756-b512-74bfaaa532cc, Email: angus.filleul@medifab.com

    10. Client: Akenz - IN LIQUIDATION (ID: 637bd1aa-d9f0-4c5a-9fd3-39721a008a38)
       Contact Name: 'Chester'
       Duplicate Count: 6
         - Contact ID: d5c60916-8123-4f52-bd95-234cf7ab8215, Email:
         - Contact ID: f46950c4-a77f-45a9-917b-2ef4e55bfcb7, Email: chester@akenz.co.nz
         - Contact ID: 82b31a46-9158-44c2-b1ef-60e6a6117dd4, Email:
         - Contact ID: 7fd11345-2917-4f10-8d7c-9b35b76d39d0, Email: chester@akenz.co.nz
         - Contact ID: e4f28111-6d9a-4b8a-b4a3-a49092136909, Email:

    ## 3. LIKELY FAILING CASE
    ----------------------------------------
    Xero contacts modified since 2025-10-05:

      Xero Contact: Galvanising Services 2018 Limited
      Local Client ID: 13b17302-270b-4cdb-b4d4-a6624fbf108b
      Contact Persons from Xero: 1

    ## 4. ROOT CAUSE ANALYSIS
    ----------------------------------------
    The issue occurs in set_client_fields() when it tries to:
      ClientContact.objects.update_or_create(
        client=client, name=name, defaults={'email': email})

    This fails when there are MULTIPLE ClientContact records with
    the same client and name combination.

    Possible causes:
    1. Historical data has duplicate contacts that were created before
       unique constraints were added
    2. Race condition during parallel sync operations
    3. Manual data entry creating duplicates

    ## 5. SUGGESTED FIX
    ----------------------------------------
    Option 1: Clean up duplicates before update_or_create
    ```python
    # In set_client_fields(), before line 282:
    # Remove duplicates first, keeping the most recent
    duplicates = ClientContact.objects.filter(
        client=client, name=name
    ).order_by('-created_at')
    if duplicates.count() > 1:
        # Keep the first (most recent), delete the rest
        for dup in duplicates[1:]:
            dup.delete()
    ```

    Option 2: Use get_or_create with exception handling
    ```python
    try:
        contact, created = ClientContact.objects.get_or_create(
            client=client, name=name,
            defaults={'email': email}
        )
        if not created and contact.email != email:
            contact.email = email
            contact.save()
    except ClientContact.MultipleObjectsReturned:
        # Handle duplicates - maybe merge or clean them
        contacts = ClientContact.objects.filter(
            client=client, name=name
        ).order_by('-created_at')
        # Keep first, update it, delete rest
        contact = contacts.first()
        contact.email = email
        contact.save()
        contacts.exclude(id=contact.id).delete()
    ```

    ## 6. TEST DATA FOR DEV
    ----------------------------------------
    To reproduce in dev, create ClientContact duplicates:

    ```python
    # In Django shell:
    from apps.client.models import Client, ClientContact
    # Pick any client
    client = Client.objects.first()
    # Create duplicates
    for i in range(25):
        ClientContact.objects.create(
            client=client,
            name='Test Duplicate',
            email=f'test{i}@example.com'
        )
    # Now run deep sync - it should fail
    ```
