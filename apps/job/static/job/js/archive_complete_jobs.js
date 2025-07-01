/**
 * Archive Complete Jobs Grid Management
 * Manages the interface for archiving completed jobs
 */
import { renderMessages } from "/static/timesheet/js/timesheet_entry/messages.js";

// State management
let availableJobs = [];
let jobsToArchive = [];

// Grid configuration
const GRID_HEIGHT_PER_ROW = 28;
const GRID_HEADER_HEIGHT = 32;
const GRID_PADDING = 2;
const MAX_ROW_COUNT = 15;

// Grid references
window.availableJobsGrid = null;
window.toArchiveJobsGrid = null;

/**
 * Calculates the appropriate grid height based on row count
 * @param {Object} grid - AG Grid instance
 * @param {string} elementId - Grid container ID
 */
function adjustGridHeight(grid, elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;

    let rowCount = 0;
    grid.forEachNode(() => rowCount++);

    const visibleRowCount = Math.min(rowCount, MAX_ROW_COUNT);
    const calculatedHeight = (visibleRowCount * GRID_HEIGHT_PER_ROW) + GRID_HEADER_HEIGHT + GRID_PADDING;

    // Set minimum height if there are no rows
    const gridHeight = Math.max(calculatedHeight, GRID_HEADER_HEIGHT + GRID_HEIGHT_PER_ROW + GRID_PADDING);

    // Update grid container height
    element.style.height = `${gridHeight}px`;

    // Update grid container classes for scrolling behavior
    if (rowCount > MAX_ROW_COUNT) {
        element.classList.add('grid-scrollable');
    } else {
        element.classList.remove('grid-scrollable');
    }
}

/**
 * Creates the column definitions for the jobs grids
 * @returns {Array} Column definitions array
 */
function createColumnDefs() {
    return [
        {
            headerCheckboxSelection: true,
            checkboxSelection: true,
            width: 50,
            suppressSizeToFit: true,
            resizable: false
        },
        {
            field: 'job_number',
            headerName: 'Job #',
            sortable: true,
            filter: true,
            minWidth: 80,
            flex: 1
        },
        {
            field: 'name',
            headerName: 'Job Name',
            sortable: true,
            filter: true,
            minWidth: 200,
            flex: 2
        },
        {
            field: 'client_name',
            headerName: 'Client',
            sortable: true,
            filter: true,
            minWidth: 150,
            flex: 1.5
        },
        {
            field: 'updated_at',
            headerName: 'Last Updated',
            sortable: true,
            filter: true,
            valueFormatter: params => {
                return new Date(params.value).toLocaleDateString();
            },
            minWidth: 120,
            flex: 1
        }
    ];
}

/**
 * Creates common grid options to be used by both grids
 * @returns {Object} Common grid options
 */
function createCommonGridOptions() {
    return {
        rowHeight: GRID_HEIGHT_PER_ROW,
        headerHeight: GRID_HEADER_HEIGHT,
        suppressPaginationPanel: true,
        rowSelection: 'multiple',
        defaultColDef: {
            resizable: true,
            sortable: true,
            filter: true
        },
        onGridSizeChanged: function(params) {
            if (params.clientWidth > 0) {
                params.api.sizeColumnsToFit();
            }
        }
    };
}

/**
 * Initializes both grid components
 */
function initializeGrids() {
    const columnDefs = createColumnDefs();
    const commonGridOptions = createCommonGridOptions();

    // Available jobs grid
    const availableGridElement = document.getElementById('available-jobs-grid');
    const availableGridOptions = {
        ...commonGridOptions,
        columnDefs: columnDefs,
        pagination: true,
        paginationPageSize: 100,
        onSelectionChanged: onAvailableSelectionChanged,
        onGridReady: function(params) {
            params.api.sizeColumnsToFit();
            adjustGridHeight(window.availableJobsGrid, 'available-jobs-grid');
        }
    };

    // To archive jobs grid
    const archiveGridElement = document.getElementById('to-archive-jobs-grid');
    const archiveGridOptions = {
        ...commonGridOptions,
        columnDefs: columnDefs,
        onSelectionChanged: onToArchiveSelectionChanged,
        onGridReady: function(params) {
            params.api.sizeColumnsToFit();
            adjustGridHeight(window.toArchiveJobsGrid, 'to-archive-jobs-grid');
        }
    };

    // Create grids using the correct API method
    window.availableJobsGrid = agGrid.createGrid(availableGridElement, availableGridOptions);
    window.toArchiveJobsGrid = agGrid.createGrid(archiveGridElement, archiveGridOptions);
}

/**
 * Updates the UI state of all buttons based on current data
 */
function updateButtonStates() {
    const btnMoveSelected = document.getElementById('btn-move-selected');
    const btnMoveAll = document.getElementById('btn-move-all');
    const btnRemoveSelected = document.getElementById('btn-remove-selected');
    const btnRemoveAll = document.getElementById('btn-remove-all');
    const btnArchiveJobs = document.getElementById('btn-archive-jobs');

    // Get selected rows
    const availableSelected = [];
    const toArchiveSelected = [];

    window.availableJobsGrid.forEachNode(node => {
        if (node.isSelected()) {
            availableSelected.push(node.data);
        }
    });

    window.toArchiveJobsGrid.forEachNode(node => {
        if (node.isSelected()) {
            toArchiveSelected.push(node.data);
        }
    });

    btnMoveSelected.disabled = availableSelected.length === 0;
    btnMoveAll.disabled = availableJobs.length === 0;
    btnRemoveSelected.disabled = toArchiveSelected.length === 0;
    btnRemoveAll.disabled = jobsToArchive.length === 0;
    btnArchiveJobs.disabled = jobsToArchive.length === 0;
}

/**
 * Handler for selection change in available jobs grid
 */
function onAvailableSelectionChanged() {
    updateButtonStates();
}

/**
 * Handler for selection change in to-archive jobs grid
 */
function onToArchiveSelectionChanged() {
    updateButtonStates();
}

/**
 * Updates both grids with current data and refreshes button states
 */
function updateGrids() {
    // Clear available jobs grid
    const availableTransaction = {
        remove: []
    };

    // First, collect all nodes to remove
    window.availableJobsGrid.forEachNode(node => {
        availableTransaction.remove.push(node.data);
    });

    // Then add new data
    availableTransaction.add = availableJobs;
    window.availableJobsGrid.applyTransaction(availableTransaction);

    // Clear to-archive grid
    const archiveTransaction = {
        remove: []
    };

    // First, collect all nodes to remove
    window.toArchiveJobsGrid.forEachNode(node => {
        archiveTransaction.remove.push(node.data);
    });

    // Then add new data
    archiveTransaction.add = jobsToArchive;
    window.toArchiveJobsGrid.applyTransaction(archiveTransaction);

    // Adjust heights after data change
    adjustGridHeight(window.availableJobsGrid, 'available-jobs-grid');
    adjustGridHeight(window.toArchiveJobsGrid, 'to-archive-jobs-grid');

    // Update button states
    updateButtonStates();
}

/**
 * Moves selected jobs from available to archive list
 */
function moveSelectedToArchive() {
    const selectedRows = [];
    window.availableJobsGrid.forEachNode(node => {
        if (node.isSelected()) {
            selectedRows.push(node.data);
        }
    });

    if (selectedRows.length === 0) return;

    // Add to archive list and remove from available list
    jobsToArchive = [...jobsToArchive, ...selectedRows];
    availableJobs = availableJobs.filter(job =>
        !selectedRows.some(selected => selected.id === job.id)
    );

    updateGrids();
}

/**
 * Moves all available jobs to archive list
 */
function moveAllToArchive() {
    jobsToArchive = [...jobsToArchive, ...availableJobs];
    availableJobs = [];

    updateGrids();
}

/**
 * Removes selected jobs from archive list back to available list
 */
function removeSelectedFromArchive() {
    const selectedRows = [];
    window.toArchiveJobsGrid.forEachNode(node => {
        if (node.isSelected()) {
            selectedRows.push(node.data);
        }
    });

    if (selectedRows.length === 0) return;

    // Add back to available list and remove from archive list
    availableJobs = [...availableJobs, ...selectedRows];
    jobsToArchive = jobsToArchive.filter(job =>
        !selectedRows.some(selected => selected.id === job.id)
    );

    updateGrids();
}

/**
 * Removes all jobs from archive list back to available list
 */
function removeAllFromArchive() {
    availableJobs = [...availableJobs, ...jobsToArchive];
    jobsToArchive = [];

    updateGrids();
}

/**
 * Fetches completed jobs from the API
 */
function fetchCompletedJobs() {
    renderMessages([{
        level: "info",
        message: "Loading completed jobs..."
    }], 'toast-container');

    fetch('/api/job/completed/')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch completed jobs');
            }
            return response.json();
        })
        .then(data => {
            // Store jobs and update grid
            availableJobs = data.results || [];
            jobsToArchive = [];

            updateGrids();
        })
        .catch(error => {
            renderMessages([{
                level: "error",
                message: "Error loading jobs: " + error.message
            }], 'toast-container');

            console.error('Error fetching jobs:', error);
        });
}

/**
 * Archives selected jobs by calling the API
 */
function archiveSelectedJobs() {
    if (jobsToArchive.length === 0) return;

    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Update UI to show progress
    const btnArchiveJobs = document.getElementById('btn-archive-jobs');
    const spinner = btnArchiveJobs.querySelector('.spinner');
    const buttonText = btnArchiveJobs.querySelector('.archive-btn-text');

    btnArchiveJobs.disabled = true;
    spinner.style.display = 'inline-block';
    buttonText.textContent = 'Archiving...';

    // Collect job IDs to archive
    const jobIds = jobsToArchive.map(job => job.id);

    // Call the API to archive jobs
    fetch('/api/job/completed/archive', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ ids: jobIds })
    })
    .then(response => response.json())
    .then(data => {
        // Reset button state
        btnArchiveJobs.disabled = false;
        spinner.style.display = 'none';
        buttonText.textContent = 'Archive Selected Jobs';

        if (data.success) {
            renderMessages([{
                level: "success",
                message: data.message
            }], 'toast-container');

            // Clear the to-archive list and refresh the available jobs
            jobsToArchive = [];
            fetchCompletedJobs();
        } else {
            const errorMsg = data.error || 'Unknown error occurred';

            let messages = [{
                level: "error",
                message: errorMsg
            }];

            // Add individual error messages if available
            if (data.errors && Array.isArray(data.errors)) {
                data.errors.forEach(err => {
                    messages.push({
                        level: "error",
                        message: err
                    });
                });
            }

            renderMessages(messages, 'toast-container');

            if (data.errors && Array.isArray(data.errors)) {
                console.error('Errors during archiving:', data.errors);
            }
        }
    })
    .catch(error => {
        // Reset button state
        btnArchiveJobs.disabled = false;
        spinner.style.display = 'none';
        buttonText.textContent = 'Archive Selected Jobs';

        renderMessages([{
            level: "error",
            message: "Error: " + error.message
        }], 'toast-container');

        console.error('Error archiving jobs:', error);
    });
}

/**
 * Initializes the page
 */
function initializePage() {
    // Initialize grids
    initializeGrids();

    // Register button event handlers
    document.getElementById('btn-move-selected').addEventListener('click', moveSelectedToArchive);
    document.getElementById('btn-move-all').addEventListener('click', moveAllToArchive);
    document.getElementById('btn-remove-selected').addEventListener('click', removeSelectedFromArchive);
    document.getElementById('btn-remove-all').addEventListener('click', removeAllFromArchive);
    document.getElementById('btn-archive-jobs').addEventListener('click', archiveSelectedJobs);

    // Fetch initial data
    fetchCompletedJobs();
}

// Initialize the module when the DOM is ready
document.addEventListener('DOMContentLoaded', initializePage);
