/**
 * Purchase Order Autosave
 * 
 * Handles automatic saving of purchase order data as changes are made.
 * Uses debouncing to prevent excessive server requests.
 * Follows the same pattern as timesheet autosave for consistency.
 */

import { renderMessages } from "./messages.js";

let deletedLineItems = [];

/**
 * Marks a line item as deleted for synchronization purposes.
 * This handles AG Grid's deleted rows separately from the form,
 * ensuring the backend correctly processes grid-level changes.
 */
export function markLineItemAsDeleted(lineItemId) {
  if (lineItemId) {
    console.log("Adding line item to deletion list:", lineItemId);
    deletedLineItems.push(lineItemId);
    console.log("Current deletion list:", deletedLineItems);
  }
}

/**
 * Creates a debounced version of a function that delays its execution until after a period of inactivity.
 *
 * @param {Function} func - The function to debounce
 * @param {number} wait - The number of milliseconds to wait before executing the function
 * @returns {Function} A debounced version of the input function
 */
function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    return new Promise((resolve) => {
      timeout = setTimeout(() => {
        resolve(func.apply(this, args));
      }, wait);
    });
  };
}

/**
 * Collects all data from the purchase order form and grid
 * @returns {Object} Object containing purchase order and line item data
 */
export function collectPurchaseOrderData() {
  console.log('Collecting purchase order data for autosave');
  
  // Get basic form data
  const purchaseOrderIdEl = document.getElementById('purchase_order_id');
  const clientIdEl = document.getElementById('client_id');
  const expectedDeliveryEl = document.getElementById('expected_delivery');
  const orderDateEl = document.getElementById('order_date');
  const statusEl = document.getElementById('status');
  
  const purchaseOrderData = {
    id: purchaseOrderIdEl ? purchaseOrderIdEl.value : null,
    client_id: clientIdEl ? clientIdEl.value : null,
    expected_delivery: expectedDeliveryEl ? expectedDeliveryEl.value : null,
    order_date: orderDateEl ? orderDateEl.value : null,
    status: statusEl ? statusEl.value : 'draft',
  };
  
  // Collect line items from the grid
  const lineItems = [];
  if (window.grid) {
    window.grid.forEachNode(node => {
      // Only include rows that have some data
      if (node.data.job || node.data.description ||
          node.data.quantity > 0 || node.data.unit_cost !== '' || node.data.price_tbc) {
        lineItems.push({...node.data});
      }
    });
  }
  
  return {
    purchase_order: purchaseOrderData,
    line_items: lineItems,
    deleted_line_items: deletedLineItems
  };
}

/**
 * Validates if the purchase order data is complete
 * @param {Object} data The data to validate
 * @returns {boolean} True if valid, false otherwise
 */
function validatePurchaseOrderData(data) {
  // Check for incomplete line items
  const incompleteItems = data.line_items.filter(
    item => !item.job || !item.description
  );
  
  // Get the purchase order ID if it exists
  const purchaseOrderIdEl = document.getElementById('purchase_order_id');
  const isPurchaseOrderEdit = purchaseOrderIdEl && purchaseOrderIdEl.value;
  
  // If there are incomplete items, show an error
  if (incompleteItems.length > 0) {
    console.log("Found incomplete line items, cannot save:", incompleteItems);
    
    // Create detailed error messages
    const messages = [];
    incompleteItems.forEach((item, index) => {
      const lineNumber = data.line_items.indexOf(item) + 1;
      const missing = !item.job ? 'job' : (!item.description ? 'description' : 'required fields');
      messages.push({
        level: "error",
        message: `Line ${lineNumber}: Missing ${missing}.`
      });
    });
    
    // Add a summary message
    messages.push({
      level: "error",
      message: "Cannot save: Please complete all required fields in line items."
    });
    
    renderMessages(messages, "purchase-order-messages");
    return false;
  }
  
  // Check if we have anything to save for new POs
  const completeItems = data.line_items.filter(
    item => item.job && item.description
  );
  
  if (
    completeItems.length === 0 &&
    data.deleted_line_items.length === 0 &&
    !isPurchaseOrderEdit
  ) {
    console.log("No data to save - no complete line items, deletions, or purchase order changes");
    return false;
  }
  
  return true;
}

/**
 * Main autosave function that collects data and sends it to the server
 */
function autosaveData() {
  console.log('Autosaving purchase order data');
  const collectedData = collectPurchaseOrderData();
  
  if (!validatePurchaseOrderData(collectedData)) {
    return Promise.resolve(false);
  }
  
  console.log("Saving data:", {
    lineItems: collectedData.line_items.length,
    deletedLineItems: collectedData.deleted_line_items.length,
  });
  
  return saveDataToServer(collectedData);
}

/**
 * Saves the collected data to the server via AJAX
 * @param {Object} collectedData The data to save
 * @returns {Promise} A promise that resolves to true if save was successful
 */
export function saveDataToServer(collectedData) {
  console.log("Autosaving purchase order data to /api/autosave-purchase-order/...", {
    line_items: collectedData.line_items.length,
    deleted_line_items: collectedData.deleted_line_items.length,
  });
  
  return fetch('/api/autosave-purchase-order/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(collectedData)
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`Server responded with status ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.success) {
      console.log('Autosave successful', data);
      // If a new PO was created (or updated), update the hidden input and global data
      if (data.id && data.po_number) {
          const purchaseOrderIdInput = document.getElementById('purchase_order_id');
          // Update hidden input only if it's currently empty (i.e., after initial creation)
          if (purchaseOrderIdInput && !purchaseOrderIdInput.value) {
              console.log(`Updating hidden input with new PO ID: ${data.id}`);
              purchaseOrderIdInput.value = data.id;
          }
          // Update the global data store regardless (to keep it in sync)
          if (window.purchaseData && window.purchaseData.purchaseOrder) {
              window.purchaseData.purchaseOrder.id = data.id;
              window.purchaseData.purchaseOrder.po_number = data.po_number;
              // Optionally update the read-only PO number field if it exists and is empty
              const poNumberInput = document.getElementById('po_number');
              if (poNumberInput && !poNumberInput.value) {
                  poNumberInput.value = data.po_number;
              }
          }
          // Clear the deleted items list after a successful save (create or update)
          // Prevents sending the same deletion request repeatedly
          if (deletedLineItems.length > 0) {
              deletedLineItems = [];
              console.log("Cleared deleted line items list after successful save.");
          }
      }
      return true;
    } else {
      // Log the more detailed error from the backend if available
      console.error('Autosave failed:', data.error || (data.messages ? data.messages.map(m => m.message).join('; ') : 'Unknown error'));
      renderMessages(
        [{
          level: "error",
          message: data.error || "Failed to save changes. Please try again."
        }],
        "purchase-order"
      );
      return false;
    }
  })
  .catch(error => {
    console.error('Autosave error:', error);
    renderMessages(
      [{
        level: "error",
        message: `Error saving changes: ${error.message}`
      }],
      "purchase-order"
    );
    return false;
  });
}

/**
 * Get the CSRF token from the page
 * @returns {string} The CSRF token
 */
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

// Debounced version of autosave
export const debouncedAutosave = debounce(autosaveData, 1500);

// Make debouncedAutosave available globally
window.debouncedAutosave = debouncedAutosave;

// Export for use in modules
export default debouncedAutosave;