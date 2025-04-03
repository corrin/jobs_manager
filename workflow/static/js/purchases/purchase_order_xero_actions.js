// workflow/static/js/purchases/purchase_order_xero_actions.js
// NOTE: This file contains functions adapted from workflow/static/js/job/job_buttons/xero_handlers.js
// for handling Xero actions specific to Purchase Orders.

import { renderMessages } from "./messages.js"; // Assuming a similar message rendering utility exists for purchases

/**
 * Updates the state of the Xero-related buttons on the Purchase Order form.
 * Adapted from handleDocumentButtons in xero_handlers.js.
 *
 * @param {('POST'|'DELETE')} method - The action performed ('POST' for creation, 'DELETE' for deletion).
 * @param {string|null} online_url - The URL to the PO in Xero (used for 'POST', null for 'DELETE').
 */
function handlePurchaseOrderXeroButtons(method, online_url = null) {
    const submitButton = document.getElementById("submit-purchase-order");
    const deleteButton = document.getElementById("deleteXeroPOButton");
    const goToXeroButton = document.getElementById("goToXeroPO");

    // Check if elements exist before manipulating them
    if (!deleteButton || !goToXeroButton) {
        console.error("Required Xero PO action buttons (Delete, GoTo) not found in the DOM.");
        // Submit button might legitimately not exist if the PO is already in Xero, so check separately
        if (method === 'DELETE' && !submitButton) {
             console.warn("Submit button not found, but this might be expected if the PO was already in Xero.");
        } else if (method === 'POST' && !submitButton) {
             console.warn("Submit button not found after POST operation. This might indicate an issue.");
        }
        // Continue if possible, but log the issue.
    }


    switch (method) {
        case "POST": // After successful submission to Xero
            if (submitButton) submitButton.style.display = "none";
            if (deleteButton) deleteButton.style.display = "inline-block";
            if (goToXeroButton) {
                goToXeroButton.style.display = "inline-block";
                if (online_url) {
                    goToXeroButton.href = online_url;
                } else {
                    goToXeroButton.href = '#'; // Default or disable if no URL
                    console.warn("No Xero URL provided after PO creation.");
                }
            }
            break;

        case "DELETE": // After successful deletion from Xero
            if (submitButton) submitButton.style.display = "inline-block";
            if (deleteButton) deleteButton.style.display = "none";
            if (goToXeroButton) {
                goToXeroButton.style.display = "none";
                goToXeroButton.href = '#'; // Reset href
            }
            break;
    }
}


/**
 * Deletes a Purchase Order from Xero.
 * Adapted from deleteXeroDocument in xero_handlers.js.
 *
 * @param {string} purchaseOrderId - The ID of the Purchase Order to delete.
 * @returns {void}
 */
export function deleteXeroPurchaseOrder(purchaseOrderId) {
    console.log(`Deleting Xero Purchase Order ID: ${purchaseOrderId}`);

    if (!purchaseOrderId) {
        renderMessages([{ level: "error", message: "Purchase Order ID is missing." }], "purchase-order-messages");
        console.error("Purchase Order ID is missing for deletion.");
        return;
    }

    if (!confirm("Are you sure you want to delete this Purchase Order from Xero? This cannot be undone.")) {
        return;
    }

    const endpoint = `/api/xero/delete_purchase_order/${purchaseOrderId}`;
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

    fetch(endpoint, {
        method: "DELETE",
        headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/json", // Optional for DELETE, but good practice
        },
    })
    .then((response) => {
        if (!response.ok) {
            // Attempt to parse error JSON, otherwise use status text
            return response.json().then(data => {
                 // Handle specific errors like Xero auth redirect if applicable
                 if (data.redirect_to_auth) {
                    renderMessages([{ level: "warning", message: "Xero session may have expired. Please try refreshing or re-authenticating." }], "purchase-order-messages");
                    // Potentially redirect here if needed: window.location.href = data.redirect_url;
                    throw new Error("Xero authentication required."); // Prevent further processing
                 }
                 throw new Error(data.message || `HTTP error! Status: ${response.status}`);
            }).catch(() => {
                // Fallback if response is not JSON or parsing fails
                throw new Error(`HTTP error! Status: ${response.status} ${response.statusText}`);
            });
        }
        return response.json(); // Expecting { success: true, messages: [...] }
    })
    .then((data) => {
        if (!data || !data.success) {
            console.error("Failed to delete Xero Purchase Order:", data?.messages);
            renderMessages(data?.messages || [{ level: "error", message: "Failed to delete Purchase Order from Xero." }], "purchase-order-messages");
            return;
        }

        console.log("Xero Purchase Order deleted successfully.");
        handlePurchaseOrderXeroButtons("DELETE"); // Update button states
        renderMessages(data.messages || [{ level: "success", message: "Purchase Order successfully deleted from Xero." }], "purchase-order-messages");

        // Optionally: Clear the xero_purchase_order_id from the hidden field if it exists
        // We need to ensure this field exists and is used consistently.
        // const xeroIdInput = document.getElementById('xero_purchase_order_id');
        // if (xeroIdInput) {
        //     xeroIdInput.value = '';
        //     // Trigger autosave if necessary
        //     // import { debouncedAutosave } from './purchase_order_autosave.js'; // Assuming autosave exists
        //     // debouncedAutosave();
        // }

    })
    .catch((error) => {
        console.error("Error deleting Xero Purchase Order:", error);
        // Avoid showing generic "Xero authentication required." message directly if it was handled above
        if (error.message !== "Xero authentication required.") {
            renderMessages([{ level: "error", message: `An error occurred: ${error.message}` }], "purchase-order-messages");
        }
    });
}

// Export handlePurchaseOrderXeroButtons if it needs to be called externally (e.g., after creation)
export { handlePurchaseOrderXeroButtons };