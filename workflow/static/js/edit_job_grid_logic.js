/*
 * File Overview:
 * ----------------
 * This file manages the creation and interaction of grids using AG Grid. It includes
 * functionality for dynamically initializing multiple grids (time, materials, adjustments)
 * across various sections (e.g., estimate, quote, reality), and includes a special revenue grid.
 * Later we might add cost with the revenue grid.
 *
 * Key Interactions:
 * - Autosave Integration:
 *   The autosave functionality depends on grid changes triggering an event that captures
 *   the data across all relevant grids. It is crucial that the APIs for each grid are correctly
 *   initialized and stored in `window.grids` to ensure autosave has access to the necessary data.
 *
 * - AG Grid API Storage:
 *   Each grid API is stored in `window.grids` once the grid is initialized. This is critical
 *   for autosave, `calculateTotalRevenue()`, and other inter-grid operations. The revenue grid is
 *   also included here, as it is required for proper calculation and data refresh.
 *
 * - AG Grid Version Compatibility:
 *   Ensure that changes align with AG Grid version 32.2.1. Be aware of deprecated properties
 *   and avoid using older APIs that may not be compatible with this version.
 *
 * Important Notes:
 * - The `onGridReady` function, inherited from `commonGridOptions`, is responsible for storing
 *   each grid's API in `window.grids`. Do not modify the initialization logic to exclude this step.
 * - Each grid API is crucial for the autosave mechanism. Breaking or missing the correct API
 *   initialization may lead to unexpected errors or the autosave failing silently.
 * - Maintain a consistent approach to API storage and avoid changes that bypass or duplicate
 *   API handling in `onGridReady`.
 */

import { createNewRow, getGridData } from '/static/js/deseralise_job_pricing.js';
import { handlePrintJob, debouncedAutosave, copyEstimateToQuote } from './edit_job_form_autosave.js';

// console.log('Grid logic script is running');

// This listener is for the entries towards the top.  The material and description fields, etc.
document.addEventListener('DOMContentLoaded', () => {
    const materialField = document.getElementById('material_gauge_quantity');
    const descriptionField = document.getElementById('job_description');

    if (!materialField || !descriptionField) {
        throw new Error('Required fields material_gauge_quantity and/or job_description are missing from page');
    }

    const autoExpand = field => {
        field.style.height = 'inherit';
        const computed = window.getComputedStyle(field);
        const height = ['border-top-width', 'padding-top', 'padding-bottom', 'border-bottom-width']
            .reduce((sum, prop) => sum + parseInt(computed.getPropertyValue(prop), 10), field.scrollHeight);
        field.style.height = `${height}px`;
    };

    [materialField, descriptionField].forEach(field => {
        field.addEventListener('input', () => autoExpand(field));
        autoExpand(field);
    });
});

// This listener is for the job pricing grid
document.addEventListener('DOMContentLoaded', function () {
    function currencyFormatter(params) {
        if (params.value === undefined) {
            // console.error("currencyFormatter error: value is undefined for the following params:", params);
            return '$0.00';  // Return a fallback value so the grid doesn't break
        }
        return '$' + params.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function numberParser(params) {
        return Number(params.newValue);
    }

    function calculateGridHeight(gridApi, numRows) {
        const rowHeight = gridApi.getSizesForCurrentTheme().rowHeight || 28;
        const headerElement = document.querySelector('.ag-header');
        const headerHeight = headerElement ? headerElement.offsetHeight : 32;

        return numRows * rowHeight + headerHeight;
    }

    function deleteIconCellRenderer(params) {
        const isLastRow = params.api.getDisplayedRowCount() === 1;
        const iconClass = isLastRow ? 'delete-icon disabled' : 'delete-icon';
        return `<span class="${iconClass}">🗑️</span>`;
    }

    function onDeleteIconClicked(params) {
        if (params.api.getDisplayedRowCount() > 1) {
            params.api.applyTransaction({ remove: [params.node.data] });
            calculateTotalRevenue(); // Recalculate totals after row deletion
        }
    }


    function onCellKeyDown(params) {
        if (params.event.key === 'Enter') {
            const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
            if (isLastRow) {
                const newRow = createNewRow(params.context.gridType);
                if (newRow) {
                    params.api.applyTransaction({ add: [newRow] });
                    setTimeout(() => {
                        params.api.setFocusedCell(params.rowIndex + 1, params.column.colId);
                        params.api.startEditingCell({
                            rowIndex: params.rowIndex + 1,
                            colKey: params.column.colId
                        });
                    }, 0);
                }
            }
        }
    }

    function createDefaultRowData(gridType) {
        return [createNewRow(gridType) || {}];  // Return the result of createNewRow as an array
    }

    function calculateTotalRevenue() {
        const revenueTotals = {
            time: { estimate: 0, quote: 0, reality: 0 },
            materials: { estimate: 0, quote: 0, reality: 0 },
            adjustments: { estimate: 0, quote: 0, reality: 0 }
        };

        const sections = ['estimate', 'quote', 'reality'];
        const gridTypes = ['Time', 'Materials', 'Adjustments'];

        sections.forEach(section => {
            gridTypes.forEach(gridType => {
                const gridKey = `${section}${gridType}Table`;
                const gridData = window.grids[gridKey];
                if (gridData && gridData.api) {
                    gridData.api.forEachNode(node => {
                        const rowCost = parseFloat(node.data.cost) || 0;
                        const rowRevenue = parseFloat(node.data.revenue) || 0;
                        const revenueType = gridType.toLowerCase();
                        revenueTotals[revenueType][section] += rowRevenue;
                    });
                }
            });
        });

        const revenueGrid = window.grids['revenueTable'];
        if (revenueGrid && revenueGrid.api) {
            revenueGrid.api.forEachNode((node, index) => {
                const data = node.data;
                switch (index) {
                    case 0: // Total Time
                        data.estimate = revenueTotals.time.estimate;
                        data.quote = revenueTotals.time.quote;
                        data.reality = revenueTotals.time.reality;
                        break;
                    case 1: // Total Materials
                        data.estimate = revenueTotals.materials.estimate;
                        data.quote = revenueTotals.materials.quote;
                        data.reality = revenueTotals.materials.reality;
                        break;
                    case 2: // Total Adjustments
                        data.estimate = revenueTotals.adjustments.estimate;
                        data.quote = revenueTotals.adjustments.quote;
                        data.reality = revenueTotals.adjustments.reality;
                        break;
                    case 3: // Total Project Cost
                        data.estimate = revenueTotals.time.estimate + revenueTotals.materials.estimate + revenueTotals.adjustments.estimate;
                        data.quote = revenueTotals.time.quote + revenueTotals.materials.quote + revenueTotals.adjustments.quote;
                        data.reality = revenueTotals.time.reality + revenueTotals.materials.reality + revenueTotals.adjustments.reality;
                        break;
                }
            })
        }

        revenueGrid.api.refreshCells();
    }


    function calculateTotalCost() {
        const totals = {
            time: { estimate: 0, quote: 0, reality: 0 },
            materials: { estimate: 0, quote: 0, reality: 0 },
            adjustments: { estimate: 0, quote: 0, reality: 0 }
        };

        const sections = ['estimate', 'quote', 'reality'];
        const gridTypes = ['Time', 'Materials', 'Adjustments'];

        sections.forEach(section => {
            gridTypes.forEach(gridType => {
                const gridKey = `${section}${gridType}Table`;
                const gridData = window.grids[gridKey];
                if (gridData && gridData.api) {
                    gridData.api.forEachNode(node => {
                        let rowCost = 0;

                        // Different cost calculation for each type
                        if (gridType === 'Time') {
                            // Cost = (minutes * wage_rate) / 60
                            const minutes = parseFloat(node.data.total_minutes) || 0;
                            const wageRate = parseFloat(node.data.wage_rate) || 0;
                            rowCost = (minutes * wageRate) / 60;
                        } else if (gridType === 'Materials') {
                            // Cost = quantity * unit_cost
                            const quantity = parseFloat(node.data.quantity) || 0;
                            const unitCost = parseFloat(node.data.unit_cost) || 0;
                            rowCost = quantity * unitCost;
                        } else if (gridType === 'Adjustments') {
                            // Cost = cost_adjustment
                            rowCost = parseFloat(node.data.cost_adjustment) || 0;
                        }

                        const costType = gridType.toLowerCase();
                        totals[costType][section] += rowCost;
                    });
                }
            });
        });

        const costGrid = window.grids['costsTable'];
        if (costGrid && costGrid.api) {
            costGrid.api.forEachNode((node, index) => {
                const data = node.data;
                switch (index) {
                    case 0: // Total Time
                        data.estimate = totals.time.estimate;
                        data.quote = totals.time.quote;
                        data.reality = totals.time.reality;
                        break;
                    case 1: // Total Materials
                        data.estimate = totals.materials.estimate;
                        data.quote = totals.materials.quote;
                        data.reality = totals.materials.reality;
                        break;
                    case 2: // Total Adjustments
                        data.estimate = totals.adjustments.estimate;
                        data.quote = totals.adjustments.quote;
                        data.reality = totals.adjustments.reality;
                        break;
                    case 3: // Total Project Cost
                        data.estimate = totals.time.estimate + totals.materials.estimate + totals.adjustments.estimate;
                        data.quote = totals.time.quote + totals.materials.quote + totals.adjustments.quote;
                        data.reality = totals.time.reality + totals.materials.reality + totals.adjustments.reality;
                        break;
                }
            });
            costGrid.api.refreshCells();
        }
    }

    const commonGridOptions = {
        rowHeight: 28,
        headerHeight: 32,
        domLayout: 'autoHeight',
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        defaultColDef: {
            sortable: true,
            resizable: true,
        },
        onGridReady: function (params) {
            // Store the grid API in the global window.grids object for easy access
            const gridKey = params.context.gridKey;  // Using the context to uniquely identify the grid
            const gridElement = document.querySelector(`#${gridKey}`);
            const initialNumRows = 1; // Default initial number of rows
            const initialGridHeight = calculateGridHeight(params.api, initialNumRows);
            //            console.log(`Grid Key: ${gridKey}, Initial Grid Height: ${initialGridHeight}`);
            gridElement.style.height = `${initialGridHeight}px`;

            window.grids[gridKey] = { api: params.api };
            // console.log(`Grid ${gridKey} initialized with API:`, window.grids[gridKey]);

            params.api.sizeColumnsToFit();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        autoSizeStrategy: {
            type: 'fitCellContents'
        },
        enterNavigatesVertically: true,
        enterNavigatesVerticallyAfterEdit: true,
        stopEditingWhenCellsLoseFocus: true,
        onCellKeyDown: onCellKeyDown,
        onRowDataUpdated: function (params) {  // Handles row updates
            const gridKey = params.context.gridKey;
            const gridElement = document.querySelector(`#${gridKey}`);
            const rowCount = params.api.getDisplayedRowCount();
            const newHeight = calculateGridHeight(params.api, rowCount);
            // console.log(`Grid Key: ${gridKey}, Updated Grid Height: ${newHeight}`);
            gridElement.style.height = `${newHeight}px`;
        },
        onCellValueChanged: function (event) {
            const gridType = event.context.gridType;
            const data = event.data;
            if (gridType === 'TimeTable') {
                data.total_minutes = (data.items || 0) * (data.mins_per_item || 0);
                data.revenue = (data.total_minutes || 0) * (data.charge_out_rate / 60.0 || 0);
            } else if (gridType === 'MaterialsTable') {
                data.revenue = (data.quantity || 0) * (data.unit_revenue || 0);
            }
            event.api.refreshCells({ rowNodes: [event.node], columns: ['revenue', 'total_minutes'], force: true });

            debouncedAutosave(event);
            calculateTotalRevenue();
            calculateTotalCost();

        }
    };

    const trashCanColumn = {
        headerName: '',
        field: '',
        width: 40,
        cellRenderer: deleteIconCellRenderer,
        onCellClicked: onDeleteIconClicked,
        cellStyle: {
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            padding: 0
        }
    };

    const timeGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {
                headerName: 'Description',
                field: 'description',
                editable: true,
                flex: 2,
                cellRenderer: (params) => {
                    // Render the description normally
                    let content = `<span>${params.value || 'No Description'}</span>`;

                    // Check if the 'link' field exists and append the action link
                    if (params.data.link) {
                        const linkLabel =
                            params.data.link === '/timesheets/overview/'
                                ? ''
                                : 'View Timesheet';
                        content += ` | <a href="${params.data.link}" target="_blank" class="action-link">${linkLabel}</a>`;
                    }

                    return content;
                },
            },
            { headerName: 'Items', field: 'items', editable: true, valueParser: numberParser },
            { headerName: 'Mins/Item', field: 'mins_per_item', editable: true, valueParser: numberParser },
            { headerName: 'Total Minutes', field: 'total_minutes', editable: false },
            {
                headerName: 'Wage Rate',
                field: 'wage_rate',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
            },
            {
                headerName: 'Charge Rate',
                field: 'charge_out_rate',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
            },
            trashCanColumn,
        ],
        rowData: [],
        context: { gridType: 'TimeTable' },
    };


    const materialsGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            { headerName: 'Item Code', field: 'item_code', editable: true },
            { headerName: 'Description', field: 'description', editable: true, flex: 2 },
            { headerName: 'Quantity', field: 'quantity', editable: true, valueParser: numberParser },
            {
                headerName: 'Cost Rate',
                field: 'unit_cost',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Retail Rate',
                field: 'unit_revenue',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            { headerName: 'Revenue', field: 'revenue', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Comments', field: 'comments', editable: true, flex: 2 },
            trashCanColumn,
        ],
        rowData: [],
        context: { gridType: 'MaterialsTable' }
    };

    const adjustmentsGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            { headerName: 'Description', field: 'description', editable: true, flex: 2 },
            {
                headerName: 'Cost Adjustment',
                field: 'cost_adjustment',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Price Adjustment',
                field: 'price_adjustment',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Revenue',
                field: 'revenue',
                editable: false,
                valueFormatter: currencyFormatter
            },
            { headerName: 'Comments', field: 'comments', editable: true, flex: 2 },
            trashCanColumn,
        ],
        rowData: [],
        context: { gridType: 'AdjustmentTable' }
    };

    const sections = ['estimate', 'quote', 'reality'];
    const workType = ['Time', 'Materials', 'Adjustments'];
    window.grids = {};

    sections.forEach(section => {
        workType.forEach(work => {
            const gridType = `${work}Table`;  // Assigning the grid type dynamically based on the work type
            const gridKey = `${section}${gridType}`;  // Create the full key for identifying the grid
            const gridElement = document.querySelector(`#${gridKey}`);


            let specificGridOptions;
            switch (gridType) {
                case 'TimeTable':
                    specificGridOptions = timeGridOptions;
                    break;
                case 'MaterialsTable':
                    specificGridOptions = materialsGridOptions;
                    break;
                case 'AdjustmentsTable':
                    specificGridOptions = adjustmentsGridOptions;
                    break;
            }

            if (!latest_job_pricings_json) {
                throw new Error('latest_job_pricings_json must be loaded before grid initialization');
            }


            const sectionData = latest_job_pricings_json[`${section}_pricing`];
            if (!sectionData) {
                console.warn(`Data not found for section "${section}". Assuming this is a new job.`);
            }

            let rowData = getGridData(section, gridType);
            if (rowData.length === 0) {
                rowData = [createNewRow(gridType)];
            }

            // console.log("Grid type: ", gridType, ", Section: ", section, ", Grid Key: ", gridKey);
            // console.log("First row of rowData during grid initialization:", rowData[0]);

            const gridOptions = {
                ...commonGridOptions,
                ...specificGridOptions,
                context: { section, gridType: `${gridType}`, gridKey: gridKey },
                rowData: rowData  // Set initial row data in gridOptions

            };

            const gridInstance = agGrid.createGrid(gridElement, gridOptions);

            // Set row data after initializing the grid
            gridInstance.setGridOption("rowData", rowData);

        });
    });


    // Grid options for Totals table (default 4 rows, autoHeight for proper resizing)
    const revenueGridOptions = {
        columnDefs: [
            { headerName: 'Category', field: 'category', editable: false },
            { headerName: 'Estimate', field: 'estimate', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Quote', field: 'quote', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Reality', field: 'reality', editable: false, valueFormatter: currencyFormatter },
        ],
        rowData: [
            { category: 'Total Time', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Materials', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Adjustments', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Project Cost', estimate: 0, quote: 0, reality: 0 }
        ],  // Default 4 rows
        domLayout: 'autoHeight',
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        onGridReady: params => {
            window.grids['revenueTable'] = { gridInstance: params.api, api: params.api };
            params.api.sizeColumnsToFit();

            calculateTotalRevenue();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        autoSizeStrategy: {
            type: 'fitCellContents'
        }
    };

    const costGridOptions = {
        columnDefs: [
            { headerName: 'Category', field: 'category', editable: false },
            { headerName: 'Estimate', field: 'estimate', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Quote', field: 'quote', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Reality', field: 'reality', editable: false, valueFormatter: currencyFormatter },
        ],
        rowData: [
            { category: 'Total Time', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Materials', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Adjustments', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Project Cost', estimate: 0, quote: 0, reality: 0 }
        ],  // Default 4 rows
        domLayout: 'autoHeight',
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        onGridReady: params => {
            window.grids['costsTable'] = { gridInstance: params.api, api: params.api };
            params.api.sizeColumnsToFit();

            calculateTotalCost();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        autoSizeStrategy: {
            type: 'fitCellContents'
        }
    };


    const revenueTableEl = document.querySelector('#revenueTable');
    if (revenueTableEl) {
        try {
            agGrid.createGrid(revenueTableEl, revenueGridOptions);
            // console.log('Revenue table initialized:', revenueGrid);
        } catch (error) {
            console.error('Error initializing revenue table:', error);
        }
    } else {
        console.error('Revenue table element not found');
    }

    const costsTableEl = document.querySelector('#costsTable');
    if (costsTableEl) {
        try {
            agGrid.createGrid(costsTableEl, costGridOptions);
            // console.log('Revenue table initialized:', revenueGrid);
        } catch (error) {
            console.error('Error initializing costs table:', error);
        }
    } else {
        console.error('Costs table element not found');
    }


    setTimeout(() => {
        const expectedGridCount = sections.length * workType.length + 2; // 3 secionds of 3 grids, plus revenue and costs totals
        const actualGridCount = Object.keys(window.grids).length;

        if (actualGridCount !== expectedGridCount) {
            console.error(`Not all grids were initialized. Expected: ${expectedGridCount}, Actual: ${actualGridCount}`);
        } else {
            console.log('All grids successfully initialized.');
        }
    }, 3000); // 3-second delay to allow all grids to finish initializing


    setTimeout(() => {
        calculateTotalRevenue();
    }, 1000);

    document.body.addEventListener('click', function (event) {
        const buttonId = event.target.id;
        const jobId = getJobIdFromUrl();

        switch (buttonId) {
            case 'copyEstimateToQuote':
                copyEstimateToQuote();
                calculateTotalCost();
                calculateTotalRevenue();
                break;

            case 'submitQuoteToClient':
                console.log('Submitting quote to client for job:', jobId);

                // TODO: add JSDocs to the following functions
                openPdfPreview(jobId);
                showQuoteModal(jobId);
                break;

            case 'reviseQuote':
                alert('Revise Quote feature coming soon!');
                break;

            case 'invoiceJobButton':
                alert('Invoice Job feature coming soon!');
                break;

            case 'printJobButton':
                handlePrintJob();
                break;

            case 'acceptQuoteButton':
                const currentDateTimeISO = new Date().toISOString();
                document.getElementById('quote_acceptance_date_iso').value = currentDateTimeISO;
                console.log(`Quote acceptance date set to: ${currentDateTimeISO}`);
                autosaveData();
                break;

            case 'contactClientButton':
                alert('Contact Client feature coming soon!');
                break;

            case 'saveEventButton':
                handleSaveEventButtonClick(jobId);
                break;

            default:
                // Random clicks not on buttons don't count - don't even log them
                break;
        }
    });
});

function getJobIdFromUrl() {
    return window.location.pathname.split('/')[2];
}

function openPdfPreview(jobId) {
    const pdfUrl = `/api/quote/${jobId}/pdf-preview/`;
    window.open(pdfUrl, '_blank');
};

function showQuoteModal(jobId, provider = 'gmail') {
    const modalHtml = `
        <div class="modal fade" id="quoteModal" tabindex="-1" role="dialog" aria-labelledby="quoteModalLabel" aria-hidden="true">
            <div class="modal-dialog" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="quoteModalLabel">Preview and Send Quote</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p>The quote has been generated. Please preview it in the opened tab and confirm if you'd like to send it to the client.</p>
                        
                        <div class="alert alert-info" role="alert">
                            <p class="mb-1">If the quote looks correct, please download the PDF from the opened tab and click "Send Quote".</p>
                            <hr>
                            <p class="mb-1">This will open your email client where you can compose your message and attach the downloaded PDF</p>
                            <hr>
                            <p class="mb-0"><b>Please ensure the PDF is properly attached before sending the email to the client.</b></p>
                        </div>

                        <div id="email-alert-container" class="alert-container"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button id="sendQuoteEmailButton" type="button" class="btn btn-primary">Send Quote</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const quoteModal = new bootstrap.Modal(document.getElementById('quoteModal'));
    quoteModal.show();

    const sendQuoteButton = document.getElementById('sendQuoteEmailButton');

    // Remove duplicated event listeners
    sendQuoteButton.replaceWith(sendQuoteButton.cloneNode(true));

    document.getElementById('sendQuoteEmailButton').addEventListener('click', async () => {
        try {
            const data = await sendQuoteEmail(jobId, provider);
            if (data.success) {
                renderMessages([{ level: 'success', message: 'Email client opened successfully.' }], 'email-alert-container');
            } else {
                renderMessages([{ level: 'error', message: 'Failed to open email client.' }], 'email-alert-container');
            }
        } catch (error) {
            renderMessages([{ level: 'error', message: `Error: ${error.message}` }], 'email-alert-container');
        }
    });
}

async function sendQuoteEmail(jobId, provider = 'gmail') {
    try {
        const response = await fetch(`/api/quote/${jobId}/send-email/`, { method: 'POST' });
        const data = await response.json();

        renderMessages(data.messages || [], 'email-alert-container');

        if (data.success && data.mailto_url) {
            const email = data.mailto_url.match(/mailto:([^?]+)/)?.[1];
            const subject = encodeURIComponent(data.mailto_url.match(/subject=([^&]+)/)?.[1]);
            const body = encodeURIComponent(data.mailto_url.match(/body=([^&]+)/)?.[1]);

            let emailUrl = '';

            if (provider === 'gmail') {
                emailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${email}&su=${subject}&body=${body}`;
            } else if (provider === 'outlook') {
                emailUrl = `https://outlook.office.com/mail/deeplink/compose?to=${email}&subject=${subject}&body=${body}`;
            } else {
                throw new Error('Unsupported email provider.');
            }

            // Open the email client in a new tab
            window.open(emailUrl, '_blank');
        } else if (!data.success) {
            console.error('Error sending email:', data.error);
        }

        return data;
    } catch (error) {
        renderMessages([{ level: 'error', message: `Error sending email: ${error.message}` }], 'email-alert-container');
        console.error('Error sending email:', error);
        throw error;
    }
}

// Function to format the event type (e.g., "manual_note" -> "Manual Note")
function formatEventType(eventType) {
    return eventType
        .replaceAll('_', ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
    }).format(date);
}

function addEventToTimeline(event, jobEventsList) {
    const eventType = formatEventType(event.event_type);

    const newEventHtml = `
        <div class="timeline-item list-group-item">
            <div class="d-flex w-100 justify-content-between">
                <div class="timeline-date text-muted small">${formatTimestamp(event.timestamp)}</div>
            </div>
            <div class="timeline-content">
                <h6 class="mb-1">${eventType}</h6>
                <p class="mb-1">${event.description}</p>
                <small class="text-muted">By ${event.staff}</small>
            </div>
        </div>
    `;
    jobEventsList.insertAdjacentHTML('afterbegin', newEventHtml);
}

function handleSaveEventButtonClick(jobId) {
    const eventDescriptionField = document.getElementById('eventDescription');
    const description = eventDescriptionField.value.trim();

    if (!description) {
        renderError('Please enter an event description.');
        return;
    }

    const jobEventsList = document.querySelector('.timeline.list-group');
    const noEventsMessage = jobEventsList.querySelector('.text-center.text-muted');

    fetch(`/api/job-event/${jobId}/add-event/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify({ description }),
    })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                renderError(data.error || 'Failed to add an event.');
                return;
            }

            if (noEventsMessage) {
                noEventsMessage.remove();
            }

            addEventToTimeline(data.event, jobEventsList);

            // Clear the input field and hide the modal
            eventDescriptionField.value = '';
            const modal = bootstrap.Modal.getInstance(document.getElementById('addJobEventModal'));
            modal.hide();
        })
        .catch(error => {
            console.error('Error adding job event:', error);
            renderError('Failed to add job event. Please try again.');
        });
}
