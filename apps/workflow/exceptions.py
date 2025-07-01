class XeroValidationError(Exception):
    """Exception raised when a Xero object is missing required fields.

    Args:
        missing_fields: Names of the missing attributes.
        entity: The entity type, such as "invoice".
        xero_id: Identifier for the record in Xero.
    """

    def __init__(self, missing_fields, entity, xero_id):
        self.missing_fields = missing_fields
        self.entity = entity
        self.xero_id = xero_id
        message = f"Missing fields {missing_fields} for {entity} {xero_id}"
        super().__init__(message)
