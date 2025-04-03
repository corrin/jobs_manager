document.addEventListener('DOMContentLoaded', function() {
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
        // Check if the row is already in the target table (prevent infinite loops if clicked fast)
        if (tbody.querySelector(`tr[data-line-id="${row.dataset.lineId}"]`)) {
            console.warn(`Row ${row.dataset.lineId} already in receivedItems. Skipping move.`);
            return;
        }
        const newRow = row.cloneNode(true);
        
        // Add received quantity input
        const receivedCell = document.createElement('td');
        receivedCell.innerHTML = `<input type="number" class="form-control form-control-sm received-qty"
                                       value="${orderedQty}" min="0" max="${orderedQty}"
                                       data-line-id="${row.dataset.lineId}">`;
        
        // Insert after the "Ordered" cell
        const orderedCell = newRow.querySelector('td:nth-child(4)');
        if (orderedCell) { // Ensure ordered cell exists before inserting
             newRow.insertBefore(receivedCell, orderedCell.nextSibling);
        } else {
             console.error('Could not find 4th cell (ordered qty) in row to insert after:', newRow);
             // Fallback: append to end? Or handle error differently?
             newRow.appendChild(receivedCell);
        }
                
        tbody.appendChild(newRow);
        row.remove();
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

    // Store all line IDs initially present
    const allLineIds = new Set();
    document.querySelectorAll('#pendingItems tr[data-line-id], #receivedItems tr[data-line-id]').forEach(row => {
        allLineIds.add(row.dataset.lineId);
    });

    // Form submission
    document.getElementById('saveChanges').addEventListener('click', async function() {
        const receivedQuantities = {};
        
        allLineIds.forEach(lineId => {
            const receivedRow = document.querySelector(`#receivedItems tr[data-line-id="${lineId}"]`);
            // Correct logic for saveChanges starts here:
            if (receivedRow) {
                const input = receivedRow.querySelector('.received-qty');
                if (input) {
                    receivedQuantities[lineId] = input.value;
                } else {
                    // Should not happen if row is in received, but good to handle
                    console.warn(`Missing quantity input for received line ID: ${lineId}`);
                    receivedQuantities[lineId] = 0;
                }
            } else {
                // If the row is not in receivedItems, it must be in pendingItems (or was never moved)
                // Its received quantity should be 0
                receivedQuantities[lineId] = 0;
            }
            // Correct logic for saveChanges ends here.
        }); // This }); corresponds to the forEach starting on line 307

        const form = document.getElementById('deliveryReceiptForm');
        // Get CSRF token from the hidden input in the main form
        const csrfToken = document.querySelector('input[name=csrfmiddlewaretoken]').value; 
        form.querySelector('#receivedQuantities').value = JSON.stringify(receivedQuantities);

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