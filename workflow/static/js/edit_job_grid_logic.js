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

import {createNewRow, getGridData} from '/static/js/deseralise_job_pricing.js';
import {handlePrintJob, copyEstimateToQuote, autosaveData} from '/static/js/edit_job_form_autosave.js';

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
        return '$' + params.value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
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
            params.api.applyTransaction({remove: [params.node.data]});
            calculateTotalRevenue(); // Recalculate totals after row deletion
        }
    }


    function onCellKeyDown(params) {
        if (params.event.key === 'Enter') {
            const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
            if (isLastRow) {
                const newRow = createNewRow(params.context.gridType);
                if (newRow) {
                    params.api.applyTransaction({add: [newRow]});
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
            time: {estimate: 0, quote: 0, reality: 0},
            materials: {estimate: 0, quote: 0, reality: 0},
            adjustments: {estimate: 0, quote: 0, reality: 0}
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
            time: {estimate: 0, quote: 0, reality: 0},
            materials: {estimate: 0, quote: 0, reality: 0},
            adjustments: {estimate: 0, quote: 0, reality: 0}
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

            window.grids[gridKey] = {api: params.api};
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
            event.api.refreshCells({rowNodes: [event.node], columns: ['revenue', 'total_minutes'], force: true});

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
            {headerName: 'Description', field: 'description', editable: true, flex: 2},
            {headerName: 'Items', field: 'items', editable: true, valueParser: numberParser},
            {headerName: 'Mins/Item', field: 'mins_per_item', editable: true, valueParser: numberParser},
            {headerName: 'Total Minutes', field: 'total_minutes', editable: false},
            {
                headerName: 'Actions',
                field: 'link',
                cellRenderer: (params) => {
                    if (params.value) {
                        if (params.value === '/timesheets/overview/') {
                            return `<a href="${params.value}" target="_blank">Go to timesheets</a>`;
                        }
                        return `<a href="${params.value}" target="_blank">View Timesheet</a>`;
                    }
                    return 'N/A';
                }
            },
            {
                headerName: 'Wage Rate',
                field: 'wage_rate',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Charge Rate',
                field: 'charge_out_rate',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {headerName: 'Revenue', field: 'revenue', editable: false, valueFormatter: currencyFormatter},
            trashCanColumn,
        ],
        rowData: [],
        context: {gridType: 'TimeTable'},
    };


    const materialsGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {headerName: 'Item Code', field: 'item_code', editable: true},
            {headerName: 'Description', field: 'description', editable: true, flex: 2},
            {headerName: 'Quantity', field: 'quantity', editable: true, valueParser: numberParser},
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
            {headerName: 'Revenue', field: 'revenue', editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Comments', field: 'comments', editable: true, flex: 2},
            trashCanColumn,
        ],
        rowData: [],
        context: {gridType: 'MaterialsTable'}
    };

    const adjustmentsGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {headerName: 'Description', field: 'description', editable: true, flex: 2},
            {
                headerName: 'Cost Adjustment',
                field: 'cost_adjustment',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Price Adjustment',
                field: 'revenue',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {headerName: 'Comments', field: 'comments', editable: true, flex: 2},
            trashCanColumn,
        ],
        rowData: [],
        context: {gridType: 'AdjustmentTable'}
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
                context: {section, gridType: `${gridType}`, gridKey: gridKey},
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
            {headerName: 'Category', field: 'category', editable: false},
            {headerName: 'Estimate', field: 'estimate', editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Quote', field: 'quote', editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Reality', field: 'reality', editable: false, valueFormatter: currencyFormatter},
        ],
        rowData: [
            {category: 'Total Time', estimate: 0, quote: 0, reality: 0},
            {category: 'Total Materials', estimate: 0, quote: 0, reality: 0},
            {category: 'Total Adjustments', estimate: 0, quote: 0, reality: 0},
            {category: 'Total Project Cost', estimate: 0, quote: 0, reality: 0}
        ],  // Default 4 rows
        domLayout: 'autoHeight',
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        onGridReady: params => {
            window.grids['revenueTable'] = {gridInstance: params.api, api: params.api};
            params.api.sizeColumnsToFit();
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
            {headerName: 'Category', field: 'category', editable: false},
            {headerName: 'Estimate', field: 'estimate', editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Quote', field: 'quote', editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Reality', field: 'reality', editable: false, valueFormatter: currencyFormatter},
        ],
        rowData: [
            {category: 'Total Time', estimate: 0, quote: 0, reality: 0},
            {category: 'Total Materials', estimate: 0, quote: 0, reality: 0},
            {category: 'Total Adjustments', estimate: 0, quote: 0, reality: 0},
            {category: 'Total Project Cost', estimate: 0, quote: 0, reality: 0}
        ],  // Default 4 rows
        domLayout: 'autoHeight',
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        onGridReady: params => {
            window.grids['costsTable'] = {gridInstance: params.api, api: params.api};
            params.api.sizeColumnsToFit();
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
        // console.log('Calling initial calculateTotals');
        calculateTotalRevenue();
    }, 1000);
});

document.addEventListener('DOMContentLoaded', function () {
    document.body.addEventListener('click', function (event) {
        const buttonId = event.target.id;

        switch (buttonId) {
            case 'copyEstimateToQuote':
                copyEstimateToQuote();
                console.log("CHECK FOR ESTIMATE TO QUOTE");
                // alert('Copied Estimate To Quote!');
                break;

            case 'submitQuoteToClient':
                alert('Submit quote feature coming soon!');
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

            default:
                // Random clicks not on buttons don't count - don't even log them
                break;
        }
    });
});
