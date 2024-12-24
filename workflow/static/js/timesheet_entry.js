// - Used to track changes and compare previous vs current row states to avoid unnecessary/repeated saves
// - Persisted to localStorage to maintain state between page refreshes
const rowStateTracker = JSON.parse(localStorage.getItem('rowStateTracker')) || {};

class ActiveJobCellEditor {
    init(params) {
        this.value = params.value;
        this.params = params;
        this.jobs = window.timesheet_data.jobs;  // These are already filtered to open jobs

        this.div = document.createElement('div');
        this.div.className = 'job-search-container';

        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.className = 'job-search-input';
        this.input.placeholder = 'Search open jobs...';

        // Automatically focus the input field when editor is opened
        setTimeout(() => this.input.focus(), 0);

        this.listDiv = document.createElement('div');
        this.listDiv.className = 'job-list';

        // Populate list with open jobs
        this.jobs.forEach(job => {
            const jobRow = document.createElement('div');
            jobRow.className = 'job-row';
            jobRow.textContent = job.job_display_name;
            jobRow.onclick = () => this.selectJob(job);
            this.listDiv.appendChild(jobRow);
        });

        // Filter as user types
        this.input.addEventListener('input', () => {
            const searchTerm = this.input.value.trim().toLowerCase();
            this.listDiv.innerHTML = ''; // Clear previous results

            const filteredJobs = this.jobs
                .filter(job => job.job_display_name.toLowerCase().includes(searchTerm))
                .slice(0, 10); // Limit results to avoid overwhelming the user

            filteredJobs.forEach(job => {
                const jobRow = document.createElement('div');
                jobRow.className = 'job-row';
                jobRow.textContent = job.job_display_name;
                jobRow.onclick = () => this.selectJob(job);
                this.listDiv.appendChild(jobRow);
            });

            // If only one job matches, select it when pressing Enter
            if (filteredJobs.length === 1) {
                this.input.addEventListener('keydown', (event) => {
                    if (event.key === 'Enter' || event.key === 'Tab') {
                        event.stopPropagation();
                        this.selectJob(filteredJobs[0]);
                    }
                });
            }
        });

        this.div.appendChild(this.input);
        this.div.appendChild(this.listDiv);
    }

    selectJob(job) {
        this.value = job.job_number;
        this.params.stopEditing();
    }

    getGui() {
        return this.div;
    }

    getValue() {
        return this.value;
    }

    // Required AG Grid lifecycle methods
    destroy() {
    }

    isPopup() {
        return true;
    }
}

window.timesheet_data = {
    timesheet_date: JSON.parse(document.getElementById('timesheet-date').textContent),
    jobs: JSON.parse(document.getElementById('jobs-data').textContent),
    time_entries: JSON.parse(document.getElementById('timesheet-entries-data').textContent),
    staff: JSON.parse(document.getElementById('staff-data').textContent)
};

function currencyFormatter(params) {
    if (params.value === undefined) return '$0.00';
    return '$' + params.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function deleteIconCellRenderer() {
    return `<span class="delete-icon">🗑️</span>`;
}

function triggerAutoCalculationForAllRows() {
    const allNodes = [];
    window.grid.forEachNode((node) => allNodes.push(node));

    allNodes.forEach((node) => {
        const jobNumber = node.data.job_number;
        if (jobNumber) {
            const job = window.timesheet_data.jobs.find(j => j.job_number === jobNumber);
            if (job) {
                node.setDataValue('job_name', job.name);
                node.setDataValue('client', job.client_name);
                node.setDataValue('job_data', job);
            }
            calculateAmounts(node.data); // Reuse existing function
        }
    });

    // Refresh affected grid cells
    window.grid.refreshCells({
        rowNodes: allNodes,
        columns: ['job_name', 'client', 'wage_amount', 'bill_amount']
    });
}


function createNewRow() {
    return {
        id: null, 
        job_number: null, 
        timesheet_date: window.timesheet_data.timesheet_date, 
        staff_id: window.timesheet_data.staff.id, 
        is_billable: true, 
        rate_type: 'Ord', 
        hours: 0, 
        description: '', 
    };
}

function calculateAmounts(data) {
    console.log('Calculating amounts for data:', data); 
    const hours = data.hours || 0;
    const minutes = hours * 60;

    console.log(data.rate_type);
    const rateMultiplier = {
        'Unpaid': 0.0,
        'Ord': 1.0,
        'Ovt': 1.5,
        'Dt': 2.0
    }[data.rate_type] || 1.0;

    const wageRate = window.timesheet_data.staff.wage_rate;
    data.wage_amount = hours * wageRate * rateMultiplier;
    console.log('Calculated wage_amount:', data.wage_amount, 'with hours:', hours, 'wage_rate:', window.timesheet_data.staff.wage_rate, 'rateMultiplier:', rateMultiplier); // Log calculation details

    const jobData = data.job_data;
    if (jobData) {
        data.bill_amount = hours * jobData.charge_out_rate;
    } else {
        data.bill_amount = 0; 
    }

    data.items = 1;
    data.mins_per_item = minutes;
}

/**
 * Determines if a row's data has been modified by comparing its previous and current states.
 * 
 * @param {Object} previousRowData - The original state of the row data
 * @param {Object} currentRowData - The new state of the row data to compare against
 * @returns {boolean} True if the row has changed, false if it remains the same
 * 
 * Purpose:
 * - Prevents unnecessary autosaves when no actual changes have been made
 * - Compares entire row states to catch all possible changes
 * - Used as a validation step before triggering autosave operations
 * 
 * Note:
 * The comparison is deep and includes all properties of the row data,
 * ensuring that even nested changes are detected
 */

function hasRowChanged(previousRowData, currentRowData) {
    // Compares the row states converting them to JSON
    const hasRowChanged = JSON.stringify(previousRowData) !== JSON.stringify(currentRowData);
    if (!hasRowChanged) {
        console.log('No changes detected, ignoring autosave');
        return hasRowChanged;
    }
    return hasRowChanged;
}

const gridOptions = {
    columnDefs: [
        {
            field: 'id',
            hide: true, // Hidden column for the database ID
            editable: false,
        },
        {
            field: 'job_number',
            headerName: 'Job #',
            flex: 1,
            minWidth: 100,
            editable: true,
            cellEditor: ActiveJobCellEditor,
            cellEditorParams: {
                values: window.timesheet_data.jobs.map(job => job.job_display_name)
            }
        },
        {
            field: 'description',
            headerName: 'Description',
            flex: 2,
            minWidth: 150,
            editable: true
        },
        {
            field: 'hours',
            headerName: 'Hours',
            flex: 1,
            minWidth: 80,
            editable: true,
            type: 'numericColumn',
            valueParser: params => Number(params.newValue),
            valueFormatter: params => params.value?.toFixed(2)
        },
        {
            field: 'is_billable',
            headerName: 'Billable',
            width: 60,
            editable: true,
            cellRenderer: 'agCheckboxCellRenderer'
        },
        {
            field: 'notes',
            headerName: 'Notes',
            flex: 2,
            minWidth: 150,
            editable: true
        },
        {
            field: 'rate_type',
            headerName: 'Rate',
            width: 70,  // Set a specific width to make it smaller
            maxWidth: 70,  // REALLY TRY AND MAKE IT SMALLER
            editable: true,
            cellEditor: 'agSelectCellEditor',
            cellEditorParams: {
                values: ['Ord', '1.5', '2.0', 'Unpaid']
            }
        },
        {
            field: 'job_name',
            headerName: 'Job Name',
            width: 100,
            editable: false
        },
        {
            field: 'client', headerName: 'Client',
            width: 100,
            editable: false
        },
        {
            field: 'wage_amount',
            headerName: 'Wage $',
            width: 70,
            valueFormatter: currencyFormatter,
            editable: false
        },
        {
            field: 'bill_amount',
            headerName: 'Bill $',
            width: 70,
            valueFormatter: currencyFormatter,
            editable: false
        },
        {
            field: 'job_data',
            headerName: 'Job Data',
            width: 0,
            hide: true, // Invisible column to make processing easier
            editable: false
        },
        {
            field: 'staff_id',
            hide: true,  // Invisible column
            editable: false
        },
        {
            field: 'timesheet_date',
            hide: true,  // Invisible column
            editable: false
        },
        {
            headerName: '',
            width: 50,
            cellRenderer: deleteIconCellRenderer,
            onCellClicked: 
            /**
             * Handles the deletion of a row when a cell is clicked in the grid.
             * 
             * @param {Object} params - The cell click event parameters from ag-Grid
             * @param {Object} params.api - The grid API
             * @param {Object} params.node - The row node that was clicked
             * @param {Object} params.node.data - The data for the clicked row
             * 
             * Business Logic:
             * - Prevents deletion of the last remaining row in the grid
             * - Assigns temporary IDs to new rows that haven't been saved
             * - Marks existing entries for deletion in the backend
             * - Removes the row from the grid's display
             * - Updates the row state tracking in localStorage
             * - Triggers an autosave after deletion
             * 
             * Safety Features:
             * - Maintains at least one row in the grid at all times
             * - Preserves deletion history for backend synchronization
             * - Handles both new (unsaved) and existing rows appropriately
             * 
             * Dependencies:
             * - Requires markEntryAsDeleted function
             * - Requires debouncedAutosave function
             * - Requires rowStateTracker object
             */
            (params) => {
                const rowCount = params.api.getDisplayedRowCount();
                console.log('node id: ', params.node.data.id);

                if (params.node.data.id == null) {
                    params.node.data.id = 'tempId';
                }

                console.log('Delete clicked for row:', {
                    id: params.node.data.id,
                    rowCount: rowCount,
                    data: params.node.data
                });

                // Only proceed if we have more than one row
                if (rowCount > 1) {
                    // Mark for deletion first if it has an ID
                    if (params.node.data.id) {
                        console.log('Marking entry for deletion:', params.node.data.id);
                        markEntryAsDeleted(params.node.data.id);
                    }

                    // Then remove from grid
                    params.api.applyTransaction({
                        remove: [params.node.data]
                    });

                    delete rowStateTracker[params.node.data.id];
                    localStorage.setItem('rowStateTracker', JSON.stringify(rowStateTracker));
                    console.log('Row removed from grid, triggering autosave');
                    debouncedAutosave();
                } else {
                    console.log('Cannot delete last row');
                }
            }
        }
    ],
    defaultColDef: {
        flex: 1,
        minWidth: 100,
        sortable: false,
        filter: false
    },
    onCellValueChanged: (params) => {
        console.log('onCellValueChanged triggered:', params);

        const previousRowData = rowStateTracker[params.node.id] || {};
        const currentRowData = { ...params.node.data };

        console.log("previous row data: ", previousRowData);
        console.log("current row data: ", currentRowData);

        const rowChanged = hasRowChanged(previousRowData, currentRowData);
        console.log('Row changed:', rowChanged);

        if (!rowChanged) {
            return;
        }

        if (currentRowData.id == null) {
            currentRowData.id = 'tempId';
        }

        const isUserEdit = params.source === 'edit';

        // If job number changes, update job name, client, and job_data
        if (params.column?.colId === 'job_number') {
            console.log('Job number changed:', params.newValue);
            const job = window.timesheet_data.jobs.find(j => j.job_number === params.newValue);
            if (job) {
                params.node.setDataValue('job_name', job.name);
                params.node.setDataValue('client', job.client_name);
                params.node.setDataValue('job_data', job); // Store the whole job object as job_data

                calculateAmounts(params.node.data);
                console.log('Refreshing cells for job_name, client, wage_amount, bill_amount');
                params.api.refreshCells({
                    rowNodes: [params.node],
                    columns: ['job_name', 'client', 'wage_amount', 'bill_amount']
                });
            }
        }

        // Recalculate amounts if rate type or hours changes
        if (['rate_type', 'hours'].includes(params.column?.colId)) {
            console.log('Rate type or hours changed:', params.column.colId, params.newValue);
            calculateAmounts(params.node.data);
            console.log('Refreshing cells for wage_amount, bill_amount');
            params.api.refreshCells({
                rowNodes: [params.node],
                columns: ['wage_amount', 'bill_amount']
            });
        }

        const rowData = params.node.data;

        const isValidRow = rowData.job_number && rowData.hours > 0 && (rowData.description.trim() !== '' || rowData.notes.trim() !== '');

        if (!isValidRow) {
            console.log('Insufficient data to save, ignoring autosave');
            return;
        }

        if (isUserEdit) {
            console.log('Is user edit? -> ', isUserEdit, 'Valid row? -> ', isValidRow);
            console.log('Row is valid and changed, triggering autosave');
            debouncedAutosave();
        }
    },
    // Add new row when Enter is pressed on last row
    onCellKeyDown: (params) => {
        if (params.event.key === 'Enter') {
            const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
            if (isLastRow) {
                const currentRowData = params.node.data;

                console.log("Job number? -> ", currentRowData.job_number);
                console.log("Hours? -> ", currentRowData.hours);
                console.log("Description? -> ", currentRowData.description && currentRowData.description.trim() !== '');
                console.log("Notes? -> ", currentRowData.notes && currentRowData.notes.trim() !== '');

                const isRowValid = Boolean(
                    currentRowData.hours > 0 &&
                    (currentRowData.description && currentRowData.description.trim() !== '')
                );

                params.api.applyTransaction({ add: [createNewRow()] });

                // Focus the first editable cell of the newly added row
                const newRowIndex = params.api.getDisplayedRowCount() - 1;
                params.api.setFocusedCell(newRowIndex, 'job_number');

                const previousRowData = rowStateTracker[params.node.id] || {};
                rowStateTracker[params.node.id] = { ...currentRowData };
                localStorage.setItem('rowStateTracker', JSON.stringify(rowStateTracker));

                const rowChanged = hasRowChanged(previousRowData, currentRowData);
                if (!rowChanged) {
                    return;
                }

                // Trigger autosave if necessary
                if (isRowValid) {
                    console.log('onCellKeyDown triggered - new row - params: ', params)
                    debouncedAutosave();
                }
            }
        }
    }
};

window.gridOptions = gridOptions;

/**
 * Retrieves the value of a specific cookie from the browser's cookies.
 * 
 * @param {string} name - The name of the cookie to retrieve
 * @returns {string|null} The decoded value of the cookie if found, null otherwise
 * 
 * Purpose:
 * - Commonly used to retrieve security tokens (like CSRF) from cookies
 * - Handles URL-encoded cookie values automatically
 * - Safely returns null if the cookie doesn't exist
 * 
 * Example Usage:
 * const csrfToken = getCookie('csrftoken');
 * 
 * Note:
 * - Searches through all browser cookies for an exact name match
 * - Automatically decodes URI-encoded cookie values
 * - Returns null if the cookie name is not found or cookies are disabled
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

/**
 * Extracts the current date from the URL pathname for paid absence processing.
 * 
 * @returns {string} The date string extracted from the URL path, expected to be in the format YYYY-MM-DD
 * 
 * Purpose:
 * - Helper function for the paid absence modal to determine which date to process
 * - Extracts date from URL path by splitting on '/' and getting second-to-last segment
 * - Used when submitting paid absence requests to ensure correct entry load (only loads the entry whose date is equivalent to that in the URL)
 * 
 * Example URL format:
 * /timesheets/day/2024-01-15/1234-567i8-903a/
 * Would return: "2024-01-15"
 * 
 * Note:
 * - Assumes date is always in penultimate position in URL path
 * - URL structure must be maintained for function to work correctly. Current URL structure: /timesheets/day/<str:date>/<uuid:staff_id>/
 * - Returns undefined if URL does not contain expected date segment
 */
function getCurrentDateFromURL() {
    const urlParts = window.location.pathname.split('/').filter(Boolean);
    return urlParts[urlParts.length - 2]; 
}

document.addEventListener('DOMContentLoaded', function () {
    // Initialize the grid
    const gridDiv = document.querySelector('#timesheet-grid');
    window.grid = agGrid.createGrid(gridDiv, gridOptions);
    console.log('Grid object:', window.grid);

    window.grid.forEachNode(node => {
        rowStateTracker[node.id] = { ...node.data };
        localStorage.setItem('rowStateTracker', JSON.stringify(rowStateTracker));
        console.log({ ...node.data });
        console.log(node.data);
    });
    console.log('Initial row state saved: ', rowStateTracker)

    // Load existing entries if any, otherwise add an empty row
    if (window.timesheet_data.time_entries?.length > 0) {
        window.grid.applyTransaction({ add: window.timesheet_data.time_entries });
        triggerAutoCalculationForAllRows();
    } else {
        window.grid.applyTransaction({
            add: [createNewRow()] // Use centralized function
        });
    }

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    /**
     * Manages the timesheet entry modal interactions and form submissions.
     * 
     * Modal Opening Handler:
     * @listens click on #new-timesheet-btn
     * @fires AJAX request to load the timesheet form
     * 
     * Form Submission Handler:
     * @listens submit on #timesheet-form
     * @fires AJAX request to save the timesheet entry
     * 
     * Business Logic:
     * 1. Modal Opening:
     *    - Loads the timesheet entry form via AJAX
     *    - Displays the form in a modal dialog
     *    - Handles loading errors with user feedback
     * 
     * 2. Form Submission:
     *    - Submits form data to server
     *    - Creates new grid entry with job details
     *    - Updates wage and bill amounts automatically
     *    - Handles validation messages and errors
     *    - Closes modal on successful submission
     * 
     * Dependencies:
     * - Requires jQuery and Bootstrap modal
     * - Requires ag-Grid instance as window.grid
     * - Requires calculateAmounts function
     * - Requires renderMessages function
     * 
     * Data Flow:
     * - Receives job data and entry details from server
     * - Integrates new entries into the grid
     * - Updates financial calculations
     * - Manages error and success messages
     */

    const modal = $('#timesheetModal');

    $('#new-timesheet-btn').on('click', function (e) {
        e.preventDefault();

        console.log('Sending AJAX request...');

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: {
                action: 'load_form'
            }, 
            success: function (response) {
                console.log('Success:', response);
                modal.find('.modal-body').html(response.form_html);
                modal.modal('show');
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });
                alert('Error loading form. Please check console for details.');
            }
        });
    });

    modal.on('submit', '#timesheet-form', function (e) {
        e.preventDefault();
        const form = $(this);

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: form.serialize(), // form.serialize() will include the CSRF token automatically
            success: function (response) {

                if (response.messages) {
                    renderMessages(response.messages); 
                }
                if (response.success) {
                    // Construct complete entry object with job data
                    const gridEntry = {
                        ...response.entry,
                        job_number: response.job.job_number,
                        job_name: response.job.name, 
                        client: response.job.client_name,
                        job_data: response.job,
                        // Both lines below will be calculated by calculateAmounts()
                        wage_amount: 0, 
                        bill_amount: 0  
                    };
            
                    window.grid.applyTransaction({ add: [gridEntry] });
            
                    // Calculate amounts for the new row
                    const lastRowNode = window.grid.getDisplayedRowAtIndex(window.grid.getDisplayedRowCount() - 1);
                    if (lastRowNode) {
                        calculateAmounts(lastRowNode.data);
                        window.grid.refreshCells({
                            rowNodes: [lastRowNode],
                            columns: ['wage_amount', 'bill_amount']
                        });
                    }
            
                    modal.modal('hide');
                }
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });

                const response = JSON.parse(xhr.responseText);
                if (response.messages) {
                    renderMessages(response.messages); 
                } else {
                    renderMessages([{ level: 'error', message: 'An unexpected error occurred.' }]);
                }
            }
        });
    });

    /**
     * Handles the click event to load the Paid Absence form in a modal.
     *
     * Purpose:
     * - Dynamically fetches and renders the Paid Absence form via AJAX.
     * - Ensures the modal is populated with the correct form content.
     * - Provides feedback to the user on errors during form loading.
     *
     * Workflow:
     * 1. Prevents the default behavior of the click event.
     * 2. Sends an AJAX POST request to the current page's URL with the action `load_paid_absence`.
     * 3. On success:
     *    - Injects the returned form HTML into the modal's body.
     *    - Displays the modal to the user.
     * 4. On error:
     *    - Logs detailed error information to the console.
     *    - Alerts the user of the issue.
     *
     * Dependencies:
     * - jQuery for AJAX handling and DOM manipulation.
     * - Bootstrap for modal functionality.
     * - Server-side handling of the `load_paid_absence` action.
     */
    $('#open-paid-absence-modal').on('click', function (e) {
        e.preventDefault();

        console.log('Loading Paid Absence form...');

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: {
                action: 'load_paid_absence'
            },
            success: function (response) {
                console.log('Sucess: ', response);
                $('#paidAbsenceModal .modal-body').html(response.form_html);
                $('#paidAbsenceModal').modal('show');
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });
                alert('Error loading form. Please check console for details.');
            }
        })
    });

    /**
     * Handles the submission of the Paid Absence form.
     *
     * Purpose:
     * - Submits the form data for creating paid absence entries via AJAX.
     * - Updates the timesheet grid with the new entries upon success.
     * - Displays error messages for issues during the submission process.
     *
     * Workflow:
     * 1. Prevents the default form submission behavior.
     * 2. Serializes the form data for transmission.
     * 3. Sends an AJAX POST request to the current page's URL with the form data.
     * 4. On success:
     *    - Hides the modal and displays success messages.
     *    - Filters the returned entries to match the current page's date.
     *    - Updates the grid with matching entries.
     * 5. On error:
     *    - Logs detailed error information to the console.
     *    - Displays error messages to the user.
     *
     * Dependencies:
     * - jQuery for AJAX handling and DOM manipulation.
     * - `getCurrentDateFromURL` for filtering entries based on the current page's date.
     * - Server-side handling of the `add_paid_absence` action.
     * - Bootstrap for modal management.
     */
    $('#paidAbsenceModal').on('submit', '#paid-absence-form', function (e) {
        e.preventDefault();
        const form = $(this).serialize();

        console.log('Submitting Paid Absence form...');

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: form,
            success: function (response) {
                if (response.success) {
                    console.log("Success: ", response.success);
                    $('#paidAbsenceModal').modal('hide');
                    renderMessages(response.messages);

                    const currentDate = getCurrentDateFromURL();
                    console.log("Current page date:", currentDate);
    
                    response.entries.forEach(entry => {
                        if (entry.timesheet_date === currentDate) {
                            console.log("Adding entry to grid:", entry);
                            window.grid.applyTransaction({ add: [entry] });
                        }
                    });
                }
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });
                renderMessages([{ level: 'error', message: 'Error adding paid absences.'}]);
            }
        });
    });
});