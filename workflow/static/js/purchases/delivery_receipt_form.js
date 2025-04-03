document.addEventListener('DOMContentLoaded', function() {
    // Get container and stock holding job info (assumed to be provided by template)
    const container = document.getElementById('deliveryReceiptContainer');
    const STOCK_HOLDING_JOB_ID = container.dataset.stockHoldingJobId;
    const STOCK_HOLDING_JOB_NAME = container.dataset.stockHoldingJobName;
    // Parse the job list from the data attribute
    let ALLOCATABLE_JOBS = [];
    try {
        ALLOCATABLE_JOBS = JSON.parse(container.dataset.jobList || '[]');
    } catch (e) {
        console.error("Failed to parse job list data:", e);
        // Handle error - maybe disable allocation?
    }

    // Select All checkboxes
    const selectAllPending = document.getElementById('selectAllPending');
    const selectAllReceived = document.getElementById('selectAllReceived');
    // Removed static NodeList declarations for pendingCheckboxes and receivedCheckboxes
    
    selectAllPending.addEventListener('change', function() {
        // Query dynamically inside the handler
        document.querySelectorAll('#pendingItems .line-checkbox').forEach(checkbox => {
            checkbox.checked = this.checked;
        });
    });
    
    selectAllReceived.addEventListener('change', function() {
         // Query dynamically inside the handler
        document.querySelectorAll('#receivedItems .line-checkbox').forEach(checkbox => {
            checkbox.checked = this.checked;
        });
    });

    // Move Selected buttons
    document.getElementById('moveSelectedToReceived').addEventListener('click', function() {
        // Query for currently checked checkboxes in the pending table
        document.querySelectorAll('#pendingItems .line-checkbox:checked').forEach(checkbox => {
            const lineId = checkbox.dataset.lineId;
            const row = checkbox.closest('tr'); // More reliable way to get the row
            if (row) { // Check if row was found
                const orderedQtyCell = row.querySelector('td:nth-child(4)'); // Get the specific cell
                if (orderedQtyCell) { // Check if cell exists
                    const orderedQty = parseInt(orderedQtyCell.textContent);
                    moveRowToReceived(row, orderedQty);
                } else {
                    console.error('Could not find ordered quantity cell for pending row:', row);
                }
            } else {
                 console.error('Could not find row for checked pending checkbox:', checkbox);
            }
        });
    });

    document.getElementById('moveAllToReceived').addEventListener('click', function() {
        // Query for all rows in the pending table
        document.querySelectorAll('#pendingItems tr[data-line-id]').forEach(row => {
            const lineId = row.dataset.lineId;
            // No need to check checkbox, move all
            const orderedQtyCell = row.querySelector('td:nth-child(4)'); // Get the specific cell
            if (orderedQtyCell) { // Check if cell exists
                const orderedQty = parseInt(orderedQtyCell.textContent);
                moveRowToReceived(row, orderedQty);
            } else {
                console.error('Could not find ordered quantity cell for pending row:', row);
            }
        });
    });

    document.getElementById('moveSelectedToPending').addEventListener('click', function() {
        // Query for currently checked checkboxes in the received table
        document.querySelectorAll('#receivedItems .line-checkbox:checked').forEach(checkbox => {
            const lineId = checkbox.dataset.lineId;
            const row = checkbox.closest('tr'); // More reliable way to get the row
            if (row) {
                moveRowToPending(row);
            } else {
                console.error('Could not find row for checked received checkbox:', checkbox);
            }
        });
    });

    document.getElementById('moveAllToPending').addEventListener('click', function() {
        // Query for all rows in the received table
        document.querySelectorAll('#receivedItems tr[data-line-id]').forEach(row => {
            const lineId = row.dataset.lineId;
            // No need to check checkbox, move all
            moveRowToPending(row);
        });
    });

    // Helper functions
    function moveRowToReceived(row, orderedQty) {
        const tbody = document.getElementById('receivedItems');
        const lineId = row.dataset.lineId; // Get lineId from original row
    
        // Check if the row is already in the target table
        if (tbody.querySelector(`tr[data-line-id="${lineId}"]`)) {
            console.warn(`Row ${lineId} already in receivedItems. Skipping move.`);
            return;
        }
    
        // Clone the basic row structure (we'll modify cells)
        const newRow = row.cloneNode(true);
        // Clear existing content except checkbox cell if needed, or rebuild
        while (newRow.cells.length > 1) { // Keep checkbox cell
            newRow.deleteCell(1);
        }
    
        // --- Rebuild cells according to the new structure ---
    
        // Get data from original row and global stock job constants
        const originalPoLineJobId = row.dataset.lineJobId || ''; // Use data attributes added in HTML
        const originalPoLineJobName = row.dataset.lineJobName || ''; // Use data attributes added in HTML
        const description = row.cells[2].textContent; // Assuming description is 3rd cell in pending
        const unitCost = row.dataset.unitCost || '0.00'; // Use data attribute

        // Determine the default allocation target
        const defaultTargetJobId = originalPoLineJobId || STOCK_HOLDING_JOB_ID;
        const defaultTargetJobName = originalPoLineJobName || STOCK_HOLDING_JOB_NAME;
    
        // 2. Job Cell (Display Only - Shows original intended job from PO)
        const jobCell = newRow.insertCell();
        jobCell.textContent = originalPoLineJobName || 'N/A'; // Show original PO line job or N/A
    
        // 3. Description Cell
        const descCell = newRow.insertCell();
        descCell.textContent = description;
    
        // 4. Ordered Cell
        const orderedCell = newRow.insertCell();
        orderedCell.textContent = orderedQty;
    
        // 5. Total Received Cell (Input)
        const totalReceivedCell = newRow.insertCell();
        totalReceivedCell.innerHTML = `<input type="number" class="form-control form-control-sm total-received-qty"
                                              value="${orderedQty}" min="0"
                                              data-line-id="${lineId}" step="any" required>`; // Default to ordered qty
    
        // 6. Allocation Details Cell
        const allocationCell = newRow.insertCell();
        allocationCell.classList.add('allocation-details-cell');
        // Set initial data attribute to store the default allocation
        const defaultAllocation = [{ jobId: defaultTargetJobId, quantity: orderedQty }];
        allocationCell.dataset.currentAllocation = JSON.stringify(defaultAllocation);

        allocationCell.innerHTML = `
            <div class="default-allocation-display">
                <span class="allocation-summary">
                    Allocated: ${orderedQty} to ${defaultTargetJobName}
                </span>
                <button type="button" class="btn btn-sm btn-outline-secondary split-allocation-btn ms-2">Split</button>
            </div>
            <div class="allocation-editor" style="display: none;">
                 <!-- JS will populate this -->
                 <div class="allocation-rows-container mb-1"></div> <!-- Container for rows -->
                 <button type="button" class="btn btn-sm btn-success add-allocation-row-btn">Add Allocation</button>
            </div>`;
    
        // 7. Unit Cost Cell
        const costCell = newRow.insertCell();
        costCell.textContent = `$${unitCost}`;
    
        // Append the fully constructed row
        tbody.appendChild(newRow);
        row.remove(); // Remove original row from pending
    }

    function moveRowToPending(row) {
        const tbody = document.getElementById('pendingItems');
         // Check if the row is already in the target table (prevent infinite loops if clicked fast)
        if (tbody.querySelector(`tr[data-line-id="${row.dataset.lineId}"]`)) {
            console.warn(`Row ${row.dataset.lineId} already in pendingItems. Skipping move.`);
            return;
        }
        const newRow = row.cloneNode(true);
        // Remove received quantity cell (should be 5th cell in received table row)
        const receivedCell = newRow.querySelector('td:nth-child(5)');
        if (receivedCell && receivedCell.querySelector('.received-qty')) { // Check it's the correct cell
             newRow.removeChild(receivedCell);
        } else {
             console.warn('Could not find 5th cell (received qty) to remove, or it was already removed:', newRow);
        }
                
        tbody.appendChild(newRow);
        row.remove();
    }

    // --- Event Listener for Split Button ---
    const receivedItemsBody = document.getElementById('receivedItems');

    receivedItemsBody.addEventListener('click', function(event) {
        if (event.target.classList.contains('split-allocation-btn')) {
            const button = event.target;
            const allocationCell = button.closest('.allocation-details-cell');
            if (!allocationCell) return;

            const defaultDisplay = allocationCell.querySelector('.default-allocation-display');
            const editor = allocationCell.querySelector('.allocation-editor');
            const rowsContainer = editor.querySelector('.allocation-rows-container');
            const currentAllocationData = JSON.parse(allocationCell.dataset.currentAllocation || '[]');

            // Hide default, show editor
            defaultDisplay.style.display = 'none';
            editor.style.display = 'block';

            // Populate editor
            renderAllocationEditor(rowsContainer, currentAllocationData);
        }

        if (event.target.classList.contains('add-allocation-row-btn')) {
             const button = event.target;
             const editor = button.closest('.allocation-editor');
             const rowsContainer = editor.querySelector('.allocation-rows-container');
             // Add a new blank row (or based on some logic)
             addAllocationRow(rowsContainer); // We'll define this next
        }
        
        // Add listener for removing allocation rows later if needed
        if (event.target.classList.contains('remove-allocation-row-btn')) {
             event.target.closest('.allocation-row').remove();
             // Add logic to update total validation if needed
             addValidationListeners(event.target.closest('.allocation-editor')); // Revalidate on remove
        }
    });

    // --- Helper Functions for Allocation Editor ---

    function renderAllocationEditor(container, allocationData) {
        container.innerHTML = ''; // Clear existing rows
        if (allocationData.length === 0) {
            // If no data (shouldn't happen with default), add one blank row
            addAllocationRow(container);
        } else {
            allocationData.forEach(alloc => addAllocationRow(container, alloc.jobId, alloc.quantity));
        }
        // Add validation listeners after rendering
        addValidationListeners(container.closest('.allocation-editor'));
    }

    function addAllocationRow(container, targetJobId = '', quantity = '') {
        // TODO: Need a way to get the list of available jobs (including Worker Admin)
        // This might require passing job list data from the template similar to STOCK_HOLDING_JOB info
        // Or making an AJAX call. For now, using a placeholder select.
        
        
        // Build job options dynamically from the ALLOCATABLE_JOBS array
        let jobOptionsHtml = '<option value="">Select Job...</option>';
        ALLOCATABLE_JOBS.forEach(job => {
            // Check if this job is the stock holding job to add '(Stock)'
            const isStockJob = job.id === STOCK_HOLDING_JOB_ID;
            const displayName = isStockJob ? `${job.name} (Stock)` : job.name;
            const selectedAttr = job.id === targetJobId ? 'selected' : '';
            jobOptionsHtml += `<option value="${job.id}" ${selectedAttr}>${displayName}</option>`;
        });
        // --- End Dynamic Options ---

        const rowDiv = document.createElement('div');
        rowDiv.innerHTML = `
            <div class="col">
                <select class="form-select form-select-sm allocation-job" required>
                    ${jobOptionsHtml}
                </select>
            </div>
            <div class="col-auto" style="width: 100px;">
                <input type="number" class="form-control form-control-sm allocation-qty"
                       value="${quantity}" min="0" step="any" required>
            </div>
            <div class="col-auto">
                <button type="button" class="btn btn-sm btn-danger remove-allocation-row-btn">&times;</button>
            </div>
        `;
        // Pre-select the job if targetJobId is provided and matches an option
        const selectElement = rowDiv.querySelector('.allocation-job');
        if (targetJobId) {
             // Find the option with the matching value and select it
             const optionToSelect = Array.from(selectElement.options).find(opt => opt.value === targetJobId);
             if (optionToSelect) {
                 optionToSelect.selected = true;
             } else {
                 console.warn(`Job ID ${targetJobId} not found in options for allocation row.`);
                 // Optionally add it dynamically if job list is comprehensive?
             }
        } else if (!targetJobId && quantity === '') {
             // If it's a truly new blank row, maybe default to stock? Or leave blank?
             // selectElement.value = STOCK_HOLDING_JOB_ID; // Example: Default new rows to stock
        }


        container.appendChild(rowDiv);
        // Add listener to the new quantity input
        const newQtyInput = rowDiv.querySelector('.allocation-qty');
        if(newQtyInput) {
            newQtyInput.addEventListener('input', () => addValidationListeners(container.closest('.allocation-editor')));
        }
    }
    
    function addValidationListeners(editorElement) {
        const row = editorElement.closest('tr');
        if (!row) return; // Exit if row not found
        const totalReceivedInput = row.querySelector('.total-received-qty');
        if (!totalReceivedInput) return; // Exit if total input not found

        const validateAllocations = () => {
            let allocatedSum = 0;
            editorElement.querySelectorAll('.allocation-qty').forEach(input => {
                allocatedSum += parseFloat(input.value || 0);
            });
            
            const totalReceived = parseFloat(totalReceivedInput.value || 0);
            const saveButton = document.getElementById('saveChanges'); // Get save button
            
            // Simple visual feedback - could be enhanced
            if (Math.abs(allocatedSum - totalReceived) > 0.001) { // Allow for floating point issues
                 editorElement.classList.add('is-invalid'); // Style the container
                 if(saveButton) saveButton.disabled = true; // Disable save if invalid
            } else {
                 editorElement.classList.remove('is-invalid');
                 if(saveButton) saveButton.disabled = false; // Enable save if valid
            }
            // Update the dataset on the parent cell
            updateAllocationData(editorElement.closest('.allocation-details-cell'));
        };

        // Remove previous listeners to avoid duplicates if re-rendering
        totalReceivedInput.removeEventListener('input', validateAllocations);
        totalReceivedInput.addEventListener('input', validateAllocations);
        
        editorElement.querySelectorAll('.allocation-qty').forEach(input => {
            input.removeEventListener('input', validateAllocations);
            input.addEventListener('input', validateAllocations);
        });
        // Initial validation run
        validateAllocations();
    }

    function updateAllocationData(allocationCell) {
        if (!allocationCell) return;
        const editor = allocationCell.querySelector('.allocation-editor');
        if (!editor || editor.style.display === 'none') {
            // If editor isn't visible, data comes from default (already set)
            // Or maybe clear it if we want to force re-split? For now, do nothing.
            return;
        }

        const allocationData = [];
        editor.querySelectorAll('.allocation-row').forEach(row => {
            const jobSelect = row.querySelector('.allocation-job');
            const qtyInput = row.querySelector('.allocation-qty');
            if (jobSelect && qtyInput && jobSelect.value && parseFloat(qtyInput.value || 0) > 0) {
                allocationData.push({
                    jobId: jobSelect.value,
                    quantity: parseFloat(qtyInput.value)
                });
            }
        });
        allocationCell.dataset.currentAllocation = JSON.stringify(allocationData);
        // Update the summary span as well?
        // const summarySpan = allocationCell.querySelector('.allocation-summary');
        // if(summarySpan) summarySpan.textContent = `Split (${allocationData.length} allocations)`;
    }

    // --- End Helper Functions ---

    // Store all line IDs initially present
    const allLineIds = new Set();
    document.querySelectorAll('#pendingItems tr[data-line-id], #receivedItems tr[data-line-id]').forEach(row => {
        allLineIds.add(row.dataset.lineId);
    });

    // Form submission
    document.getElementById('saveChanges').addEventListener('click', async function(event) {
        event.preventDefault(); // Prevent default form submission
        const lineAllocationsData = {};

        // Clear previous validation states potentially set by backend errors later
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

        allLineIds.forEach(lineId => {
            const receivedRow = document.querySelector(`#receivedItems tr[data-line-id="${lineId}"]`);
            
            if (receivedRow) {
                const totalReceivedInput = receivedRow.querySelector('.total-received-qty');
                const totalReceived = parseFloat(totalReceivedInput.value || 0);
                const allocationCell = receivedRow.querySelector('.allocation-details-cell');
                
                // Ensure latest allocation data is stored in the dataset before reading
                updateAllocationData(allocationCell);
                const currentAllocations = JSON.parse(allocationCell.dataset.currentAllocation || '[]');

                lineAllocationsData[lineId] = {
                    total_received: totalReceived,
                    allocations: currentAllocations
                };

            } else {
                // Line is still in pending
                lineAllocationsData[lineId] = {
                    total_received: 0,
                    allocations: []
                };
            }
        });

        // Basic check if any allocation data was generated (optional)
        if (Object.keys(lineAllocationsData).length === 0) {
             console.warn("No allocation data found to submit.");
             // Maybe alert the user?
             return;
        }

        // Proceed with submission - Backend will handle validation
        const form = document.getElementById('deliveryReceiptForm');
        const csrfToken = document.querySelector('input[name=csrfmiddlewaretoken]').value;
        const hiddenInput = form.querySelector('#receivedQuantities'); // Find the original input
        
        // Ensure the hidden input exists before modifying
        if (hiddenInput) {
            hiddenInput.name = 'line_allocations'; // Rename input
            hiddenInput.value = JSON.stringify(lineAllocationsData);
        } else {
            console.error("Hidden input field '#receivedQuantities' not found!");
            alert("Error preparing form data. Cannot save."); // Inform user
            return;
        }

        // Disable save button during submission
        event.target.disabled = true;
        event.target.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

        try {
            // Use the current URL as the action if form.action is not set
            const formAction = form.action || window.location.href;
            const response = await fetch(formAction, {
                method: 'POST',
                body: new FormData(form),
                headers: {
                    'X-CSRFToken': csrfToken // Use the retrieved token
                }
            });

            if (response.ok) {
                // TODO: This URL should ideally be passed from the template, not hardcoded.
                window.location.href = "/delivery-receipts/"; 
            } else {
                const data = await response.json();
                alert(data.error || 'An error occurred while saving the delivery receipt.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while saving the delivery receipt.');
        }
    });
});