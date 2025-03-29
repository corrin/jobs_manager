/**
 * Delivery Receipt Form Handling
 * 
 * Uses AG Grid for line items management, focusing on received quantities
 */

import { renderMessages } from './messages.js';
import { updateJobsList } from './job_section.js';
import { updateSummarySection } from './summary.js';

// Track autosave state
let lastAutosaveSuccess = true;

// Helper function to convert status code to display name
function getStatusDisplay(status) {
    const statusMap = {
        'draft': 'Draft',
        'submitted': 'Submitted to Supplier',
        'partially_received': 'Partially Received',
        'fully_received': 'Fully Received',
        'void': 'Voided'
    };
    return statusMap[status] || status;
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    
    // Parse JSON data
    const jobsDataElement = document.getElementById('jobs-data');
    const lineItemsDataElement = document.getElementById('line-items-data');
    const purchaseOrderDataElement = document.getElementById('purchase-order-data');
    
    // Store data globally
    window.purchaseData = {
        jobs: jobsDataElement ? JSON.parse(jobsDataElement.textContent) : [],
        lineItems: lineItemsDataElement ? JSON.parse(lineItemsDataElement.textContent) : [],
        purchaseOrder: purchaseOrderDataElement ? JSON.parse(purchaseOrderDataElement.textContent) : {}
    };
    
    console.log('Purchase order data loaded:', window.purchaseData);
    
    // Initialize grid only if we have the container
    const gridDiv = document.querySelector('#delivery-receipt-lines-grid');
    if (!gridDiv) {
        console.error('Grid container not found');
        return;
    }

    // Define grid columns
    const columnDefs = [
        {
            field: 'job_display_name',
            headerName: 'Job',
            flex: 2,
            editable: false
        },
        {
            field: 'description',
            headerName: 'Description',
            flex: 2,
            editable: false
        },
        {
            field: 'quantity',
            headerName: 'Ordered Qty',
            flex: 1,
            editable: false,
            valueFormatter: params => params.value.toFixed(2)
        },
        {
            field: 'received_quantity',
            headerName: 'Received Qty',
            flex: 1,
            editable: true,
            valueFormatter: params => params.value.toFixed(2),
            cellStyle: params => {
                if (params.value > params.data.quantity) {
                    return { color: 'red' };
                }
                return null;
            }
        },
        {
            field: 'unit_cost',
            headerName: 'Unit Cost',
            flex: 1,
            editable: false,
            valueFormatter: params => params.value ? params.value.toFixed(2) : 'TBC'
        }
    ];

    // Grid options
    const gridOptions = {
        columnDefs: columnDefs,
        rowData: window.purchaseData.lineItems,
        defaultColDef: {
            sortable: true,
            filter: true,
            resizable: true,
        },
        onCellValueChanged: onCellValueChanged,
        onGridReady: onGridReady,
        suppressRowClickSelection: true,
        rowHeight: 40,
        domLayout: 'autoHeight'
    };

    // Initialize the grid
    new agGrid.Grid(gridDiv, gridOptions);
    window.grid = gridOptions;

    // If we have an existing purchase order, populate the form
    if (window.purchaseData.purchaseOrder && window.purchaseData.purchaseOrder.id) {
        // Set the purchase order ID
        document.getElementById('purchase_order_id').value = window.purchaseData.purchaseOrder.id;
        
        // Set the PO number
        if (window.purchaseData.purchaseOrder.po_number) {
            document.getElementById('po_number').value = window.purchaseData.purchaseOrder.po_number;
        }
        
        // Set the supplier
        if (window.purchaseData.purchaseOrder.supplier) {
            document.getElementById('client_id').value = window.purchaseData.purchaseOrder.supplier;
            document.getElementById('client_name').value = window.purchaseData.purchaseOrder.supplier_name;
        }
        
        // Set the dates
        if (window.purchaseData.purchaseOrder.order_date) {
            document.getElementById('order_date').value = window.purchaseData.purchaseOrder.order_date.split('T')[0];
        }
        
        if (window.purchaseData.purchaseOrder.expected_delivery) {
            document.getElementById('expected_delivery').value = window.purchaseData.purchaseOrder.expected_delivery.split('T')[0];
        }
        
        if (window.purchaseData.purchaseOrder.status) {
            document.getElementById('status').value = window.purchaseData.purchaseOrder.status;
        }
    }

    // Set up the submit button handler
    const submitButton = document.getElementById('submit-delivery-receipt');
    if (submitButton) {
        submitButton.addEventListener('click', handleSubmit);
    }

    // Initialize the jobs list
    updateJobsList(window.purchaseData.jobs);
});

/**
 * Handle cell value changes in the grid
 */
function onCellValueChanged(event) {
    const data = event.data;
    const field = event.column.colId;
    
    if (field === 'received_quantity') {
        const receivedQty = parseFloat(event.newValue) || 0;
        const orderedQty = parseFloat(data.quantity);
        
        // Validate received quantity
        if (receivedQty < 0) {
            event.api.refreshCells({
                rowNodes: [event.node],
                columns: ['received_quantity'],
                force: true
            });
            return;
        }
        
        // Update the data
        data.received_quantity = receivedQty;
        
        // Update summary section
        updateSummarySection(window.purchaseData.lineItems);
    }
}

/**
 * Handle grid ready event
 */
function onGridReady(event) {
    // Auto-size columns to fit content
    event.api.sizeColumnsToFit();
    
    // Update summary section
    updateSummarySection(window.purchaseData.lineItems);
}

/**
 * Handle form submission
 */
async function handleSubmit() {
    const submitButton = document.getElementById('submit-delivery-receipt');
    const messagesContainer = document.getElementById('delivery-receipt-messages');
    
    try {
        // Disable submit button
        submitButton.disabled = true;
        
        // Collect data
        const data = collectDeliveryReceiptData();
        
        // Validate data
        if (!validateDeliveryReceiptData(data)) {
            throw new Error('Invalid data. Please check the received quantities.');
        }
        
        // Submit data
        const response = await submitDeliveryReceiptData(data);
        
        if (response.success) {
            // Show success message
            renderMessages(messagesContainer, [{
                type: 'success',
                message: 'Delivery receipt completed successfully.'
            }]);
            
            // Redirect after a short delay
            setTimeout(() => {
                window.location.href = response.redirect_url;
            }, 1500);
        } else {
            throw new Error(response.error || 'Failed to complete delivery receipt.');
        }
    } catch (error) {
        console.error('Error submitting delivery receipt:', error);
        renderMessages(messagesContainer, [{
            type: 'error',
            message: error.message
        }]);
    } finally {
        // Re-enable submit button
        submitButton.disabled = false;
    }
}

/**
 * Collect all data from the delivery receipt form and grid
 */
function collectDeliveryReceiptData() {
    const purchaseOrderId = document.getElementById('purchase_order_id').value;
    
    // Collect line items from the grid
    const lineItems = [];
    if (window.grid) {
        window.grid.api.forEachNode(node => {
            lineItems.push({
                id: node.data.id,
                received_quantity: node.data.received_quantity
            });
        });
    }
    
    return {
        purchase_order_id: purchaseOrderId,
        line_items: lineItems
    };
}

/**
 * Validate the delivery receipt data
 */
function validateDeliveryReceiptData(data) {
    if (!data.purchase_order_id) {
        throw new Error('Purchase order ID is required.');
    }
    
    if (!data.line_items || data.line_items.length === 0) {
        throw new Error('No line items found.');
    }
    
    // Check if any received quantities are invalid
    for (const item of data.line_items) {
        const lineItem = window.purchaseData.lineItems.find(li => li.id === item.id);
        if (!lineItem) continue;
        
        if (item.received_quantity < 0) {
            throw new Error('Received quantity cannot be negative.');
        }
        
        if (item.received_quantity > lineItem.quantity) {
            throw new Error(`Received quantity cannot exceed ordered quantity for item: ${lineItem.description}`);
        }
    }
    
    return true;
}

/**
 * Submit the delivery receipt data to the server
 */
async function submitDeliveryReceiptData(data) {
    const form = document.getElementById('delivery-receipt-submit-form');
    const formData = new FormData(form);
    
    // Add the data to the form
    formData.append('purchase_order_data', JSON.stringify(data));
    
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error submitting data:', error);
        throw error;
    }
}

/**
 * Get the CSRF token from the page
 */
function getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
} 