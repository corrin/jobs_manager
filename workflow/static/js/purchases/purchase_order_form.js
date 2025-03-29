/**
 * Purchase Order Form Handling
 * 
 * Uses AG Grid for line items management, using the timesheet pattern
 */

import { debouncedAutosave, markLineItemAsDeleted, collectPurchaseOrderData, saveDataToServer } from './purchase_order_autosave.js';
import { ActiveJobCellEditor } from './job_cell_editor.js';
import { renderMessages } from './messages.js';
import { updateJobsList } from './job_section.js';
import { updateSummarySection } from './summary.js';

// Track autosave state - default to true since data is already saved when loading
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
    
    // Parse JSON data from HTML elements
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
    
    // Update submit button state after data is loaded
    updateSubmitButtonState();
    
    // Initialize grid only if we have the container
    const gridDiv = document.querySelector('#purchase-order-lines-grid');
    if (!gridDiv) {
        console.error('Grid container not found');
        return;
    }
    
    // Create grid options
    const gridOptions = {
        columnDefs: [
            {
                headerName: 'Job',
                field: 'job',
                editable: true,
                cellEditor: ActiveJobCellEditor,
                valueFormatter: params => {
                    if (!params.value) return '';
                    const job = window.purchaseData.jobs.find(j => j.id === params.value);
                    return job ? job.job_display_name : '';
                }
            },
            {
                headerName: 'Description',
                field: 'description',
                editable: true
            },
            {
                headerName: 'Quantity',
                field: 'quantity',
                editable: true,
                valueParser: params => {
                    if (params.newValue === '' || params.newValue === null) return 1;
                    return Number(params.newValue);
                }
            },
            {
                headerName: 'Cost to be confirmed',
                field: 'price_tbc',
                width: 90,
                editable: true,
                cellRenderer: params => {
                    return `<input type="checkbox" ${params.value ? 'checked' : ''} />`;
                },
                cellEditor: 'agCheckboxCellEditor',
                cellEditorParams: {
                    useFormatter: true
                },
                onCellClicked: params => {
                    // Toggle the checkbox value when clicked
                    const newValue = !params.value;
                    params.node.setDataValue('price_tbc', newValue);
                    
                    // If setting to true, immediately clear the unit cost
                    if (newValue) {
                        params.node.setDataValue('unit_cost', null);
                    }
                    
                    // Refresh the unit_cost cell to update editability
                    params.api.refreshCells({
                        rowNodes: [params.node],
                        columns: ['unit_cost', 'total'],
                        force: true
                    });
                },
                onCellValueChanged: params => {
                    // When price_tbc changes, refresh the unit_cost cell to update editability
                    params.api.refreshCells({
                        rowNodes: [params.node],
                        columns: ['unit_cost', 'total'],
                        force: true
                    });
                    
                    // If price_tbc is true, set unit_cost to null
                    if (params.value) {
                        params.node.setDataValue('unit_cost', null);
                    }
                }
            },
            {
                headerName: 'Unit Cost',
                field: 'unit_cost',
                editable: params => !params.data.price_tbc, // Not editable when price_tbc is true
                valueParser: params => {
                    if (params.data.price_tbc) return null;
                    if (params.newValue === '' || params.newValue === null) return null;
                    return Number(params.newValue);
                },
                valueFormatter: params => {
                    if (params.data.price_tbc) return 'TBC';
                    if (params.value === null) return '';
                    return `$${Number(params.value).toFixed(2)}`;
                },
                cellRenderer: params => {
                    if (params.data.price_tbc) return `<span class="text-muted">TBC</span>`;
                    if (params.value === null) return '';
                    return `$${Number(params.value).toFixed(2)}`;
                }
            },
            {
                headerName: 'Total',
                field: 'total',
                valueGetter: params => {
                    // Assert that quantity exists and is a number
                    console.assert(params.data.quantity !== undefined, 'Quantity is undefined');
                    
                    // Return TBC if price_tbc is true or unit_cost is null
                    if (params.data.price_tbc || params.data.unit_cost === null) {
                        return 'TBC';
                    }
                    
                    return params.data.quantity * params.data.unit_cost;
                },
                valueFormatter: params => {
                    if (params.value === 'TBC') return 'TBC';
                    return `$${Number(params.value).toFixed(2)}`;
                },
                cellStyle: params => {
                    // Skip validation if job is empty (new row) or price is TBC
                    if (!params.data.job || params.data.price_tbc || params.value === 'TBC') return null;
                    
                    const jobId = params.data.job;
                    const job = window.purchaseData.jobs.find(j => j.id === jobId);
                    
                    // Assert necessary conditions
                    console.assert(job, `Job with ID ${jobId} not found`);
                    console.assert(job.estimated_materials !== undefined,
                        `Job ${job.job_number} missing estimated_materials`);
                    
                    // Calculate total cost for this job from all rows
                    let jobTotal = 0;
                    params.api.forEachNode(node => {
                        if (node.data.job === jobId && !node.data.price_tbc && node.data.unit_cost !== null) {
                            jobTotal += node.data.quantity * node.data.unit_cost;
                        }
                    });
                    
                    return jobTotal > job.estimated_materials ? { backgroundColor: "#fff3cd" } : null;
                },
                cellRenderer: params => {
                    // If value is TBC, render it as such
                    if (params.value === 'TBC') return '<span class="text-muted">TBC</span>';
                    
                    // Format the value with currency
                    const formattedValue = `$${Number(params.value).toFixed(2)}`;
                    
                    // Skip validation if job is empty (new row)
                    if (!params.data.job) return formattedValue;
                    
                    const jobId = params.data.job;
                    const job = window.purchaseData.jobs.find(j => j.id === jobId);
                    
                    // Assert necessary conditions
                    console.assert(job, `Job with ID ${jobId} not found`);
                    console.assert(job.estimated_materials !== undefined,
                        `Job ${job.job_number} missing estimated_materials`);
                    
                    // Calculate total cost for this job from all rows
                    let jobTotal = 0;
                    params.api.forEachNode(node => {
                        if (node.data.job === jobId && !node.data.price_tbc && node.data.unit_cost !== null) {
                            jobTotal += node.data.quantity * node.data.unit_cost;
                        }
                    });
                    
                    return jobTotal > job.estimated_materials
                        ? `<div style="background-color: #fff3cd">⚠️ ${formattedValue}</div>`
                        : formattedValue;
                }
            },
            {
                headerName: '',
                field: 'delete',
                width: 50,
                cellRenderer: deleteIconCellRenderer,
                onCellClicked: (params) => {
                    deleteRow(params.api, params.node);
                }
            }
        ],
        rowData: [],
        defaultColDef: {
            flex: 1,
            minWidth: 100,
            resizable: true
        },
        onCellValueChanged: onCellValueChanged,
        domLayout: 'autoHeight',
        // Handle keyboard navigation
        onCellKeyDown: (params) => {
            const { event, api, node, column } = params;
            const isLastRow = params.node.rowIndex === params.api.getDisplayedRowCount() - 1;
            const colId = column.getColId();
            
            // Handle different key combinations
            if (event.key === 'Enter') {
                if (colId === 'delete') {
                    // Delete row when Enter is pressed in delete column
                    deleteRow(api, node);
                } else if (colId === 'unit_cost' && !event.shiftKey) {
                    // Add new row when Enter is pressed in unit_cost column
                    event.stopPropagation();
                    createNewRowShortcut(api);
                    return false;
                }
            } else if (event.key === 'Tab' && !event.shiftKey && isLastRow && colId === 'unit_cost') {
                // Add new row when Tab is pressed in unit_cost column of last row
                createNewRowShortcut(api);
            }
        }
    };
    
    // Initialize with existing data or a blank row
    gridOptions.rowData = window.purchaseData.lineItems.length ? window.purchaseData.lineItems : [createNewRow()];
    
    // Create the grid
    window.grid = agGrid.createGrid(gridDiv, gridOptions);
    console.log('Grid initialized with data:', gridOptions.rowData);
    
    // Initial adjustment
    adjustGridHeight();
    
    // Initialize job summary section
    updateJobSummary();
    
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
        
        // If the status is not draft, make specific fields read-only
        if (window.purchaseData.purchaseOrder.status && window.purchaseData.purchaseOrder.status !== 'draft') {
            // Add a notice at the top of the form
            const formElement = document.getElementById('purchase-order-details-form');
            const noticeDiv = document.createElement('div');
            noticeDiv.className = 'alert alert-info mb-3';
            noticeDiv.innerHTML = `<i class="bi bi-info-circle me-2"></i>This purchase order is in <strong>${getStatusDisplay(window.purchaseData.purchaseOrder.status)}</strong> status. Some fields cannot be edited.`;
            formElement.prepend(noticeDiv);
            
            // Make specific fields read-only (but not expected_delivery)
            const fieldsToLock = ['client_name', 'client_id', 'po_number', 'order_date'];
            fieldsToLock.forEach(fieldId => {
                const field = document.getElementById(fieldId);
                if (field) {
                    field.setAttribute('readonly', true);
                    field.classList.add('form-control-plaintext');
                    field.classList.remove('form-control');
                }
            });
            
            // Make the grid read-only
            window.setTimeout(() => {
                if (gridOptions && gridOptions.api) {
                    gridOptions.api.setGridOption('readOnly', true);
                }
            }, 500);
        }
    } else {
        // Set today's date for order date for new purchase orders
        const today = new Date();
        const formattedDate = today.toISOString().split('T')[0]; // Format as YYYY-MM-DD
        document.getElementById('order_date').value = formattedDate;
    }
    
    // Using autosave - no save button needed
    
    // Cell value change handler
    function onCellValueChanged(params) {
        // If this is the last row and contains data, add a new empty row
        const isLastRow = params.node.rowIndex === params.api.getDisplayedRowCount() - 1;
        const hasData = params.data.job || params.data.description ||
                        params.data.quantity !== '' || params.data.unit_cost !== '';
        
        // Only add a new row if the purchase order is in draft status
        const isDraft = !window.purchaseData.purchaseOrder ||
                       !window.purchaseData.purchaseOrder.status ||
                       window.purchaseData.purchaseOrder.status === 'draft';
        
        if (isLastRow && hasData && isDraft) {
            createNewRowShortcut(params.api);
        }
        
        // Determine which cells to refresh based on what changed
        const jobId = params.data.job;
        const changedField = params.colDef.field;
        const isCostRelatedChange = ['job', 'quantity', 'unit_cost', 'price_tbc'].includes(changedField);
        
        if (jobId && isCostRelatedChange) {
            // Find all nodes with this job
            const nodesToRefresh = [];
            params.api.forEachNode(node => {
                if (node.data.job === jobId) {
                    nodesToRefresh.push(node);
                }
            });
            
            // Assert we found at least this row
            console.assert(nodesToRefresh.length > 0, 'No rows found for job refresh');
            
            // Refresh total cells for all related job rows
            params.api.refreshCells({
                rowNodes: nodesToRefresh,
                columns: ['total'],
                force: true
            });
            
            // Check if materials cost exceeds estimated cost
            const job = window.purchaseData.jobs.find(j => j.id === jobId);
            if (job) {
                // Calculate total cost for this job from all rows
                let jobTotal = 0;
                params.api.forEachNode(node => {
                    if (node.data.job === jobId && !node.data.price_tbc && node.data.unit_cost !== null) {
                        jobTotal += node.data.quantity * node.data.unit_cost;
                    }
                });
                
                // Show warning if cost exceeds estimate
                if (jobTotal > job.estimated_materials) {
                    renderMessages(
                        [{
                            level: "warning",
                            message: `Materials cost $${jobTotal.toFixed(2)} exceeds estimated $${job.estimated_materials.toFixed(2)}.`
                        }],
                        "purchase-order"
                    );
                }
            }
        } else {
            // Update only this row's total
            params.api.refreshCells({
                rowNodes: [params.node],
                columns: ['total'],
                force: true
            });
        }
        
        // Update job summary section
        updateJobSummary();
        
        adjustGridHeight();
        debouncedAutosave().then(success => {
            lastAutosaveSuccess = success;
            updateSubmitButtonState();
        });
    }
    
    // Function to create a new empty row
    function createNewRow() {
        return {
            job: '',
            description: '',
            quantity: 1,
            unit_cost: null,
            price_tbc: false
        };
    }
    
    // Function to render delete icon
    function deleteIconCellRenderer() {
        return `<span class="delete-icon">🗑️</span>`;
    }
    
    // Function to create new row with shortcut
    function createNewRowShortcut(api) {
        // Check if purchase order is in draft status
        if (window.purchaseData.purchaseOrder &&
            window.purchaseData.purchaseOrder.status &&
            window.purchaseData.purchaseOrder.status !== 'draft') {
            
            // Show message that rows cannot be added
            renderMessages(
                [{
                    level: "error",
                    message: `Cannot add new items. This purchase order is in ${getStatusDisplay(window.purchaseData.purchaseOrder.status)} status.`
                }],
                "purchase-order"
            );
            return;
        }
        
        // Add the new row
        const result = api.applyTransaction({
            add: [createNewRow()]
        });
        
        // Assert the row was added successfully
        console.assert(result && result.add && result.add.length === 1,
            'Failed to add new row');
        
        // Focus the first cell of the new row
        setTimeout(() => {
            const lastRowIndex = api.getDisplayedRowCount() - 1;
            api.setFocusedCell(lastRowIndex, 'job');
            adjustGridHeight();
        }, 100);
    }
    
    // Function to delete a row
    function deleteRow(api, node) {
        // Assert that api and node exist
        console.assert(api && node, 'API or node is undefined in deleteRow');
        
        // Check if purchase order is in draft status
        if (window.purchaseData.purchaseOrder &&
            window.purchaseData.purchaseOrder.status &&
            window.purchaseData.purchaseOrder.status !== 'draft') {
            
            // Show message that rows cannot be deleted
            renderMessages(
                [{
                    level: "error",
                    message: `Cannot delete items. This purchase order is in ${getStatusDisplay(window.purchaseData.purchaseOrder.status)} status.`
                }],
                "purchase-order"
            );
            return;
        }
        
        // Only delete if there's more than one row
        if (api.getDisplayedRowCount() > 1) {
            // If the row has an ID, mark it for deletion on the server
            if (node.data.id && node.data.id !== 'tempId') {
                markLineItemAsDeleted(node.data.id);
            }
            
            // Delete the row and verify success
            const result = api.applyTransaction({ remove: [node.data] });
            console.assert(result && result.remove && result.remove.length === 1,
                'Failed to remove row');
                
            adjustGridHeight();
            updateJobSummary();
            debouncedAutosave().then(success => {
                lastAutosaveSuccess = success;
                updateSubmitButtonState();
            });
        }
    }
    
    // Function to adjust grid height based on number of rows
    function adjustGridHeight() {
        const gridElement = document.getElementById('purchase-order-lines-grid');
        
        // Assert grid element exists
        console.assert(gridElement, "Grid container not found");
        if (!gridElement) return;

        // Count rows and calculate appropriate height
        let rowCount = 0;
        window.grid.forEachNode(() => rowCount++);
        
        const rowHeight = 40;
        const headerHeight = 50;
        const padding = 5;
        const minHeight = 150; // Minimum height for the grid
        
        // Set grid height
        const height = Math.max(rowCount * rowHeight + headerHeight + padding, minHeight);
        gridElement.style.height = `${height}px`;
    }
    
    // Removed saveOrder function as we're using autosave instead
    
    // Add event listeners for all form fields with the autosave-input class
    const autosaveInputs = document.querySelectorAll('.autosave-input');
    autosaveInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Update our data model if this is the status field
            if (this.id === 'status' && window.purchaseData.purchaseOrder) {
                window.purchaseData.purchaseOrder.status = this.value;
            }
            debouncedAutosave().then(success => {
                lastAutosaveSuccess = success;
                updateSubmitButtonState();
            });
        });
    });

    // Add event listener for the "Submit to Xero" button
    const submitButton = document.getElementById('submit-purchase-order');
    if (submitButton) {
        submitButton.addEventListener('click', function() {
            submitPurchaseOrderToXero();
        });
    }
});

/**
 * Updates the submit button state based on autosave status and purchase order status
 */
function updateSubmitButtonState() {
    const submitButton = document.getElementById('submit-purchase-order');
    if (!submitButton) return;

    const isDraft = !window.purchaseData.purchaseOrder ||
                   !window.purchaseData.purchaseOrder.status ||
                   window.purchaseData.purchaseOrder.status === 'draft';

    console.log('updateSubmitButtonState:', {
        isDraft,
        lastAutosaveSuccess,
        status: window.purchaseData.purchaseOrder?.status,
        purchaseOrder: window.purchaseData.purchaseOrder
    });

    if (isDraft && lastAutosaveSuccess) {
        submitButton.disabled = false;
        submitButton.title = "Submit purchase order to Xero";
    } else {
        submitButton.disabled = true;
        submitButton.title = isDraft ? 
            "Please wait for changes to save before submitting" : 
            "Only draft purchase orders can be submitted";
    }
}

/**
 * Submits the purchase order to Xero
 */
function submitPurchaseOrderToXero() {
    // Get the purchase order ID
    const purchaseOrderId = document.getElementById('purchase_order_id').value;
    
    // Show loading state
    const submitButton = document.getElementById('submit-purchase-order');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Submitting...';
    submitButton.disabled = true;
    
    // If we don't have a purchase order ID yet, we need to save the form first
    if (!purchaseOrderId) {
        // Collect the form data
        const formData = collectPurchaseOrderData();
        
        // Save the form data
        saveDataToServer(formData)
            .then(response => {
                if (response && response.po_number) {
                    // Now we have a purchase order ID, so we can submit to Xero
                    const newPurchaseOrderId = document.getElementById('purchase_order_id').value;
                    if (newPurchaseOrderId) {
                        // Submit to Xero with the new ID
                        submitToXero(newPurchaseOrderId, submitButton, originalText);
                    } else {
                        // Still no ID, show error
                        renderMessages(
                            [{
                                level: "error",
                                message: "Could not create purchase order. Please try again."
                            }],
                            "purchase-order-messages"
                        );
                        
                        // Reset button and update state
                        submitButton.innerHTML = originalText;
                        lastAutosaveSuccess = false;
                        updateSubmitButtonState();
                    }
                } else {
                    // Error saving
                    renderMessages(
                        [{
                            level: "error",
                            message: "Could not create purchase order. Please try again."
                        }],
                        "purchase-order-messages"
                    );
                    
                    // Reset button and update state
                    submitButton.innerHTML = originalText;
                    lastAutosaveSuccess = false;
                    updateSubmitButtonState();
                }
            })
            .catch(error => {
                console.error("Error saving purchase order:", error);
                
                // Show error message
                renderMessages(
                    [{
                        level: "error",
                        message: `Error saving purchase order: ${error.message}`
                    }],
                    "purchase-order-messages"
                );
                
                // Reset button and update state
                submitButton.innerHTML = originalText;
                lastAutosaveSuccess = false;
                updateSubmitButtonState();
            });
    } else {
        // We already have a purchase order ID, so we can submit to Xero directly
        submitToXero(purchaseOrderId, submitButton, originalText);
    }
}

/**
 * Submit the purchase order to Xero
 */
function submitToXero(purchaseOrderId, submitButton, originalText) {
    // Submit to Xero
    fetch(`/api/xero/purchase-order/${purchaseOrderId}/create/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server responded with status ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Show success message
            renderMessages(
                data.messages || [{
                    level: "success",
                    message: "Purchase order submitted to Xero successfully."
                }],
                "purchase-order-messages"
            );
            
            // Hide the submit button
            submitButton.style.display = 'none';
            
            // Reload the page after a short delay
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            // Show error message
            renderMessages(
                data.messages || [{
                    level: "error",
                    message: data.error || "Failed to submit purchase order to Xero."
                }],
                "purchase-order-messages"
            );
            
            // Reset button and update state
            submitButton.innerHTML = originalText;
            lastAutosaveSuccess = false;
            updateSubmitButtonState();
        }
    })
    .catch(error => {
        console.error("Error submitting purchase order to Xero:", error);
        
        // Show error message
        renderMessages(
            [{
                level: "error",
                message: `Error submitting purchase order to Xero: ${error.message}`
            }],
            "purchase-order-messages"
        );
        
        // Reset button and update state
        submitButton.innerHTML = originalText;
        lastAutosaveSuccess = false;
        updateSubmitButtonState();
    });
}

/**
 * Get the CSRF token from the page
 */
function getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

/**
 * Updates the job summary section with details about each job's materials costs
 * Follows the pattern from timesheet's updateSummarySection function
 */
function updateJobSummary() {
    const grid = window.grid;
    if (!grid) {
        console.error("Grid instance not found.");
        return;
    }

    // Create a map to track job totals
    const jobTotals = new Map();
    
    // Iterate through grid rows to calculate summary data
    grid.forEachNode((node) => {
        const jobId = node?.data?.job;
        if (!jobId) return;
        
        const job = window.purchaseData.jobs.find(j => j.id === jobId);
        if (!job) return;
        
        // Calculate cost for this line item
        const quantity = node.data.quantity || 0;
        const unitCost = node.data.price_tbc || node.data.unit_cost === null ? 0 : (node.data.unit_cost || 0);
        const lineCost = quantity * unitCost;
        
        // Add to job total
        if (!jobTotals.has(jobId)) {
            jobTotals.set(jobId, {
                id: jobId,
                job_number: job.job_number,
                name: job.name,
                client_name: job.client_name,
                estimated_materials: job.estimated_materials,
                materials_purchased: 0
            });
        }
        
        jobTotals.get(jobId).materials_purchased += lineCost;
    });
    
    // Convert map to array and sort by job number
    const jobSummaries = Array.from(jobTotals.values())
        .sort((a, b) => {
            // Convert both job numbers to strings and compare
            const aNum = String(a.job_number || '');
            const bNum = String(b.job_number || '');
            return aNum.localeCompare(bNum);
        });
    
    // Update the job cards
    updateJobsList(jobSummaries);
    
    // Update the summary section
    updateSummarySection();
}