# workflow/views/xero_po_creator.py
import json
import logging
from datetime import date, datetime

from django.http import JsonResponse
from django.utils import timezone
from xero_python.accounting.models import LineItem
from xero_python.accounting.models import PurchaseOrder as XeroPurchaseOrder

# Import models
from apps.purchasing.models import PurchaseOrder
from apps.workflow.models import XeroAccount

# Import base class and helpers
from .xero_base_manager import XeroDocumentManager
from .xero_helpers import clean_payload, convert_to_pascal_case, format_date

logger = logging.getLogger("xero")


class XeroPurchaseOrderManager(XeroDocumentManager):
    """Simplified Xero PO sync handler"""

    _is_po_manager = True

    def __init__(self, purchase_order: PurchaseOrder):
        super().__init__(client=purchase_order.supplier, job=None)
        self.purchase_order = purchase_order

    def can_sync_to_xero(self) -> bool:
        """Check if PO is ready for Xero sync (has required fields)"""
        if not self.purchase_order.supplier:
            logger.info(
                "PO %s cannot sync to Xero - missing supplier", self.purchase_order.id
            )
            return False

        if not self.purchase_order.supplier.xero_contact_id:
            logger.info(
                "PO %s cannot sync to Xero - supplier %s missing xero_contact_id",
                self.purchase_order.id,
                self.purchase_order.supplier.id,
            )
            return False

        # First check if we have any lines at all
        if not self.purchase_order.po_lines.exists():
            logger.info(
                "PO %s cannot sync to Xero - Xero requires at least one line item",
                self.purchase_order.id,
            )
            return False

        # Then check if at least one line has required fields
        has_valid_line = any(
            line.description and line.unit_cost is not None
            for line in self.purchase_order.po_lines.all()
        )

        if not has_valid_line:
            logger.info(
                (
                    "PO %s cannot sync to Xero - no valid lines found "
                    "(need at least one with description and unit_cost)"
                ),
                self.purchase_order.id,
            )
            return False

        return True

    def get_xero_id(self) -> str | None:
        """Returns the Xero ID if the local PO has one."""
        zero_uuid = "00000000-0000-0000-0000-000000000000"
        if (
            self.purchase_order
            and self.purchase_order.xero_id
            and str(self.purchase_order.xero_id) != zero_uuid
        ):
            return str(self.purchase_order.xero_id)
        return None

    def _get_account_code(self) -> str | None:
        """
        Return the Purchases account code for PO line creation, or None if
        it's not found.
        """
        try:
            return XeroAccount.objects.get(
                account_name__iexact="Purchases"
            ).account_code
        except XeroAccount.DoesNotExist:
            logger.warning(
                (
                    "Could not find 'Purchases' account in Xero accounts, "
                    "omitting account code for PO lines."
                )
            )
            return None
        except XeroAccount.MultipleObjectsReturned:
            accounts = XeroAccount.objects.filter(account_name__iexact="Purchases")
            logger.warning(
                f"Found multiple 'Purchases' accounts: "
                f"{[(a.account_name, a.account_code, a.xero_id) for a in accounts]}. "
                f"Omitting account code."
            )
            return None

    def _get_xero_update_method(self):
        """Returns the Xero API method for creating/updating POs."""
        # This method handles both create and update (PUT/POST)
        return self.xero_api.update_or_create_purchase_orders

    def _get_local_model(self):
        """Returns the local Django model class."""
        return PurchaseOrder

    def _is_zero_uuid(self, uuid_str: str) -> bool:
        """Checks if an UUID is the standard zero UUID"""
        zero_uuid = "00000000-0000-0000-0000-000000000000"
        return str(uuid_str) == zero_uuid

    def _fetch_uuid(self, po_number: str):
        """
        Fetches the real UUID of a PO on Xero based on its number

        Args:
            po_number: The number of the PO to search for

        Returns:
            Tuple containing (uuid, updated_date_utc) if found or (None, None) if not
        """
        try:
            get_method = self.xero_api.get_purchase_orders
            (
                search_response,
                _,
                _,
            ) = get_method(self.xero_tenant_id, _return_http_data_only=False)

            if (
                hasattr(search_response, "purchase_orders")
                and search_response.purchase_orders
            ):
                for po in search_response.purchase_orders:
                    if (
                        hasattr(po, "purchase_order_number")
                        and po.purchase_order_number == po_number
                    ):
                        if not self._is_zero_uuid(po.purchase_order_id):
                            logger.info(
                                f"Found real UUID for PO {self.purchase_order.id}: "
                                f"{po.purchase_order_id}"
                            )
                            return po.purchase_order_id, po.updated_date_utc

                logger.warning(
                    f"Aditional query returned zero UUID for PO "
                    f"{self.purchase_order.id}"
                )
        except Exception as e:
            logger.error(f"Error consulting real UUID for PO {po_number}: {str(e)}")

        return None, None

    def _save_po_with_xero_data(
        self, xero_id: str | None, online_url: str, updated_date_utc: datetime | None
    ) -> None:
        """
        Saves PO data with Xero information.

        Args:
            xero_id: Xero ID to be saved, None for not saving ID
            online_url: Xero online URL
            updated_date_utc: Xero update date, or None to use now()
        """
        update_fields = ["online_url"]

        self.purchase_order.online_url = online_url

        if updated_date_utc:
            self.purchase_order.xero_last_synced = updated_date_utc
            update_fields.append("xero_last_synced")
        else:
            self.purchase_order.xero_last_synced = timezone.now()

        if xero_id:
            self.purchase_order.xero_id = xero_id
            update_fields.append("xero_id")

        self.purchase_order.save(update_fields=update_fields)

    def _handle_xero_response(self, response) -> JsonResponse:
        """
        Process Xero's API response and updates the local model

        Args:
            response: Xero API Response

        Returns:
            JsonResponse with success or error status
        """
        if not hasattr(response, "purchase_orders") or not response.purchase_orders:
            msg = (
                f"Xero API response missing or empty 'purchase_orders' for PO "
                f"{self.purchase_order.id}"
            )
            logger.error(msg)
            return JsonResponse(
                {
                    "success": False,
                    "error": msg,
                    "details": "Missing or empty 'purchase_orders' attribute",
                },
                status=502,
            )

        logger.info("Response received from Xero API: %s", response)
        xero_po = response.purchase_orders[0]
        xero_po_url = (
            f"https://go.xero.com/Accounts/Payable/PurchaseOrders/Edit/"
            f"{xero_po.purchase_order_id}/"
        )

        if hasattr(xero_po, "validation_errors") and xero_po.validation_errors:
            error_messages = "; ".join(
                [
                    err.get("message", "Unknown error")
                    for err in xero_po.validation_errors
                ]
            )
            logger.warning(
                f"Xero validation errors for PO {self.purchase_order.id}: "
                f"{error_messages}"
            )

        if self._is_zero_uuid(xero_po.purchase_order_id):
            logger.warning(
                f"Xero returned zero UUID for PO {self.purchase_order.id}. "
                f"Trying to consult real ID."
            )

            real_uuid, real_updated_date = self._fetch_uuid(
                self.purchase_order.po_number
            )

            if real_uuid:
                self._save_po_with_xero_data(real_uuid, xero_po_url, real_updated_date)

                return JsonResponse(
                    {
                        "success": True,
                        "xero_id": str(real_uuid) if real_uuid else None,
                        "online_url": xero_po_url,
                    }
                )

            logger.error(
                f"""
                Could not find real UUID for PO {self.purchase_order.id}.
                Attempting to create it again.
                """.strip()
                # CORRIN: WHAT ON EARTH IS THIS?
            )
            try:
                # Preparar o payload novamente
                xero_doc = self.get_xero_document(type="create")
                raw_payload = xero_doc.to_dict()
                cleaned_payload = clean_payload(raw_payload)
                payload = {"PurchaseOrders": [convert_to_pascal_case(cleaned_payload)]}

                # Chamar a API do Xero novamente para criar a PO
                update_method = self._get_xero_update_method()
                logger.info(f"Retrying creation for PO {self.purchase_order.id}")
                retry_response, _, _ = update_method(
                    self.xero_tenant_id,
                    purchase_orders=payload,
                    summarize_errors=False,
                    _return_http_data_only=False,
                )

                # Verificar se a nova tentativa teve sucesso
                # CORRIN: WHAT! retry?  Fail early.  This code is a mess.
                if (
                    hasattr(retry_response, "purchase_orders")
                    and retry_response.purchase_orders
                ):
                    retry_po = retry_response.purchase_orders[0]
                    retry_url = (
                        f"https://go.xero.com/Accounts/Payable/PurchaseOrders/Edit/"
                        f"{retry_po.purchase_order_id}/"
                    )

                    # Verificar se ainda recebemos um UUID zero
                    if not self._is_zero_uuid(retry_po.purchase_order_id):
                        # Sucesso na segunda tentativa!
                        logger.info(
                            f"""
                            Successfully created PO on retry with UUID:
                            {retry_po.purchase_order_id}
                            """.strip()
                        )
                        self._save_po_with_xero_data(
                            retry_po.purchase_order_id,
                            retry_url,
                            retry_po.updated_date_utc,
                        )
                        return JsonResponse(
                            {
                                "success": True,
                                "xero_id": str(retry_po.purchase_order_id),
                                "online_url": retry_url,
                                "retry": True,
                            }
                        )
                    else:
                        logger.warning(
                            f"""
                            Retry still returned zero UUID for PO
                            {self.purchase_order.id}
                            """.strip()
                        )
                else:
                    logger.warning(
                        f"""
                        Retry did not return any purchase orders for PO
                        {self.purchase_order.id}
                        """.strip()
                    )

            except Exception as e:
                logger.error(
                    f"Error during retry for PO {self.purchase_order.id}: {str(e)}"
                )

            # If we reached this point, both the original and the retry attempt failed
            # to obtain a valid UUID
            # We save without the UUID, but with the URL and synchronisation date
            self._save_po_with_xero_data(None, xero_po_url, timezone.now())
            return JsonResponse(
                {
                    "success": True,
                    "xero_id": None,
                    "online_url": xero_po_url,
                    "warning": (
                        "Could not obtain a valid UUID from Xero, "
                        "but the PO may have been created"
                    ),
                }
            )

        self._save_po_with_xero_data(
            xero_po.purchase_order_id, xero_po_url, xero_po.updated_date_utc
        )

        logger.info(
            f"""
            Successfully synced PO {self.purchase_order.id} to Xero.
            Xero ID: {xero_po.purchase_order_id}
            """.strip()
        )
        return JsonResponse(
            {
                "success": True,
                "xero_id": str(xero_po.purchase_order_id),
                "online_url": xero_po_url,
            }
        )

    def state_valid_for_xero(self) -> bool:
        """
        Checks if the purchase order is in a valid state for Xero operations.
        For initial creation, we require 'draft' status.
        For updates, we allow any status as long as the PO has a Xero ID.
        """
        # If we're updating an existing PO in Xero, allow any status
        if self.get_xero_id():
            return True

        # For initial creation/sending, we require 'draft'
        return self.purchase_order.status == "draft"

    def get_line_items(self) -> list[LineItem]:
        """
        Generates purchase order-specific LineItems for the Xero API payload.
        """
        logger.info("Starting get_line_items for PO")
        xero_line_items = []
        account_code = self._get_account_code()

        if not self.purchase_order:
            logger.error("Purchase order object is missing in get_line_items.")
            return []  # Or raise error

        for line in self.purchase_order.po_lines.all():  # Correct related name
            description = line.description
            # Prepend Job Number if available
            if line.job:
                description = f"{line.job.job_number} - {description}"

            line_item_data = {
                "description": (
                    f"Price to be confirmed - {description}"
                    if line.price_tbc
                    else description
                ),
                "quantity": float(line.quantity),
                "unit_amount": float(line.unit_cost) if line.unit_cost else 0.0,
            }

            if line.item_code:
                line_item_data["item_code"] = (
                    line.item_code
                )  # Corrigido para snake_case

            # Add account code only if found
            if account_code:
                line_item_data["account_code"] = account_code

            try:
                # Append the LineItem object directly
                xero_line_items.append(LineItem(**line_item_data))
            except Exception as e:
                logger.error(
                    f"""
                    Error creating xero-python LineItem object for PO line
                    {line.id}: {e}
                    """.strip(),
                    exc_info=True,
                )
                # Decide whether to skip this line or raise the error

        logger.info(
            f"Finished get_line_items for PO. Prepared {len(xero_line_items)} items."
        )
        return xero_line_items

    def get_xero_document(self, type="create") -> XeroPurchaseOrder:
        """
        Returns a xero_python PurchaseOrder object based on the specified type.
        """
        if not self.purchase_order:
            raise ValueError("PurchaseOrder object is missing.")

        status_map = {
            "draft": "DRAFT",
            "submitted": "SUBMITTED",
            "partially_received": "AUTHORISED",
            "fully_received": "AUTHORISED",
            "deleted": "DELETED",
        }

        if type == "delete":
            xero_id = self.get_xero_id()
            if not xero_id:
                raise ValueError("Cannot delete a purchase order without a Xero ID.")
            # Deletion via API usually means setting status to DELETED via update
            return XeroPurchaseOrder(purchase_order_id=xero_id, status="DELETED")
        elif type in ["create", "update"]:
            # Build the common document data dictionary using snake_case keys
            order_date = self.purchase_order.order_date
            if isinstance(order_date, str):
                order_date = date.fromisoformat(order_date)
            document_data = {
                "purchase_order_number": self.purchase_order.po_number,
                "contact": self.get_xero_contact(),  # Uses base class method
                "date": format_date(order_date),
                "line_items": self.get_line_items(),
                "status": status_map.get(self.purchase_order.status, "DRAFT"),
            }

            # Add optional fields if they exist
            if self.purchase_order.expected_delivery:
                expected_delivery = self.purchase_order.expected_delivery
                if isinstance(expected_delivery, str):
                    expected_delivery = date.fromisoformat(expected_delivery)
                document_data["delivery_date"] = format_date(expected_delivery)
            if self.purchase_order.reference:
                document_data["reference"] = self.purchase_order.reference

            # Add the Xero PurchaseOrderID only for updates
            if type == "update":
                xero_id = self.get_xero_id()
                if not xero_id:
                    raise ValueError(
                        "Cannot update a purchase order without a Xero ID."
                    )
                document_data["purchase_order_id"] = xero_id

            # Log the data just before creating the XeroPurchaseOrder object
            logger.info(f"Data for XeroPurchaseOrder init: {document_data}")
            try:
                return XeroPurchaseOrder(**document_data)
            except Exception as e:
                logger.error(
                    f"Error initializing xero_python PurchaseOrder model: {e}",
                    exc_info=True,
                )
                raise  # Re-raise the error
        else:
            raise ValueError(f"Unknown document type for Purchase Order: {type}")

    def sync_to_xero(self) -> JsonResponse:
        """Sync current PO state to Xero and update local model with Xero data.

        Returns:
            JsonResponse: Always returns a JsonResponse with:
                - success (bool): Whether the operation succeeded
                - On success: xero_id and online_url fields
                - On failure: error and exception_type fields
        """
        has_data = self.can_sync_to_xero()
        if not has_data:
            logger.warning(
                "Cannot sync PO %s to Xero - not yet ready - validation failed",
                self.purchase_order.id,
            )
            return JsonResponse(
                {
                    "success": True,
                    "error": (
                        "Purchase order is not ready for sync. "
                        "Please complete all required fields."
                    ),
                    "exception_type": "ValidationError",
                    "is_incomplete_po": True,
                }
            )

        try:
            # Determine if creating or updating
            action = "update" if self.get_xero_id() else "create"
            xero_doc = self.get_xero_document(type=action)

            raw_payload = xero_doc.to_dict()
            logger.info("Xero document data (including None values): %s", raw_payload)

            cleaned_payload = clean_payload(raw_payload)
            payload = {"PurchaseOrders": [convert_to_pascal_case(cleaned_payload)]}
            logger.info(
                f"Serialized payload for {action}: {json.dumps(payload, indent=4)}"
            )
        except Exception as e:
            logger.error(
                f"""
                Error preparing or serializing Xero document for PO
                {self.purchase_order.id}: {str(e)}
                """.strip(),
                exc_info=True,
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Failed to prepare Xero document: {str(e)}",
                    "exception_type": type(e).__name__,
                },
                status=500,
            )

        try:
            update_method = self._get_xero_update_method()
            logger.info(f"Calling Xero API method: {update_method.__name__}")

            response, _, _ = update_method(
                self.xero_tenant_id,
                purchase_orders=payload,
                summarize_errors=False,
                _return_http_data_only=False,
            )

            return self._handle_xero_response(response)
        except Exception as e:
            # has_data already checked at the top of sync_to_xero()
            logger.error(
                f"Failed to sync PO {self.purchase_order.id} to Xero: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {"success": False, "error": str(e), "exception_type": type(e).__name__},
                status=500,
            )

    def delete_document(self):
        """
        Deletes the purchase order in Xero by setting its status to DELETED.
        Updates the local PurchaseOrder record by clearing the Xero ID.
        Returns a JsonResponse suitable for the calling view.
        """
        xero_id = self.get_xero_id()
        if not xero_id:
            logger.error(
                f"Cannot delete PO {self.purchase_order.id}: No Xero ID found."
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "Purchase Order not found in Xero (no Xero ID).",
                },
                status=404,
            )

        logger.info(
            f"""
            Attempting to delete purchase order {self.purchase_order.id}
            (Xero ID: {xero_id}) by setting status to DELETED.
            """.strip()
        )

        try:
            # Prepare the minimal payload for deletion (setting status)
            xero_document = XeroPurchaseOrder(
                purchase_order_id=xero_id, status="DELETED"
            )
            payload = convert_to_pascal_case(clean_payload(xero_document.to_dict()))
            payload_list = {"PurchaseOrders": [payload]}
            logger.info(
                f"Serialized payload for delete: {json.dumps(payload_list, indent=4)}"
            )

        except Exception as e:
            logger.error(
                f"Error serializing XeroDocument for delete: {str(e)}", exc_info=True
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Failed to serialize data for Xero deletion: {str(e)}",
                },
                status=500,
            )

        try:
            # Use the update method to set the status to DELETED
            update_method = self._get_xero_update_method()
            logger.info(
                f"Calling Xero API method for deletion: {update_method.__name__}"
            )
            response, http_status, http_headers = update_method(
                self.xero_tenant_id,
                purchase_orders=payload_list,
                summarize_errors=False,
                _return_http_data_only=False,
            )

            logger.info(f"Xero API Response Content (delete): {response}")
            logger.info(f"Xero API HTTP Status (delete): {http_status}")

            # Process the response
            if (
                response
                and hasattr(response, "purchase_orders")
                and response.purchase_orders
            ):
                xero_po_data = response.purchase_orders[0]

                # Check for validation errors (though less likely for a status update)
                if (
                    hasattr(xero_po_data, "validation_errors")
                    and xero_po_data.validation_errors
                ):
                    error_details = "; ".join(
                        [f"{err.message}" for err in xero_po_data.validation_errors]
                    )
                    logger.error(
                        f"""
                        Xero validation errors during delete for PO
                        {self.purchase_order.id}: {error_details}
                        """.strip()
                    )
                    return JsonResponse(
                        {
                            "success": False,
                            "error": (
                                f"Xero validation errors during delete: "
                                f"{error_details}"
                            ),
                        },
                        status=400,
                    )

                # Confirm status is DELETED (or check http_status)
                if (
                    getattr(xero_po_data, "status", None) == "DELETED"
                    or http_status < 300
                ):
                    # Clear local Xero ID and update status
                    # (optional, could just clear ID)
                    self.purchase_order.xero_id = None
                    self.purchase_order.xero_last_synced = timezone.now()
                    self.purchase_order.status = "deleted"
                    self.purchase_order.save(
                        update_fields=["xero_id", "xero_last_synced", "status"]
                    )

                    logger.info(
                        f"""
                        Successfully deleted purchase order {self.purchase_order.id}
                        in Xero (Xero ID: {xero_id}).
                        """.strip()
                    )
                    return JsonResponse({"success": True, "action": "delete"})
                else:
                    error_msg = (
                        f"Xero did not confirm deletion status for PO "
                        f"{self.purchase_order.id}. Status: "
                        f"{getattr(xero_po_data, 'status', 'Unknown')}"
                    )
                    logger.error(error_msg)
                    return JsonResponse(
                        {"success": False, "error": error_msg}, status=500
                    )
            else:
                error_msg = "Unexpected or empty response from Xero API during delete."
                logger.error(
                    f"{error_msg} for PO {self.purchase_order.id}. Response: {response}"
                )
                return JsonResponse({"success": False, "error": error_msg}, status=500)

        except Exception as e:
            logger.error(
                f"""
                Unexpected error deleting PO {self.purchase_order.id} from Xero:
                {str(e)}
                """.strip(),
                exc_info=True,
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": f"An unexpected error occurred during deletion: {str(e)}",
                },
                status=500,
            )
