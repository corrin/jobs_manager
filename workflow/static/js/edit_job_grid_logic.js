/*
 * File Overview:
 * ----------------
 * This file manages the creation and interaction of grids using AG Grid. It includes
 * functionality for dynamically initializing multiple grids (time, materials, adjustments)
 * across various sections (e.g., estimate, quote, reality), and includes a special totals grid.
 *
 * Key Interactions:
 * - Autosave Integration:
 *   The autosave functionality depends on grid changes triggering an event that captures
 *   the data across all relevant grids. It is crucial that the APIs for each grid are correctly
 *   initialized and stored in `window.grids` to ensure autosave has access to the necessary data.
 *
 * - AG Grid API Storage:
 *   Each grid API is stored in `window.grids` once the grid is initialized. This is critical
 *   for autosave, `calculateTotals()`, and other inter-grid operations. The totals grid is
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


// console.log('Grid logic script is running');

// This listener is for the entries towards the top.  The material and description fields, etc.
document.addEventListener('DOMContentLoaded', function () {
    const materialField = document.getElementById('materialGaugeQuantity');
    const descriptionField = document.getElementById('description');

    function autoExpand(field) {
        field.style.height = 'inherit';
        const computed = window.getComputedStyle(field);
        const height = parseInt(computed.getPropertyValue('border-top-width'), 10)
            + parseInt(computed.getPropertyValue('padding-top'), 10)
            + field.scrollHeight
            + parseInt(computed.getPropertyValue('padding-bottom'), 10)
            + parseInt(computed.getPropertyValue('border-bottom-width'), 10);
        field.style.height = `${height}px`;
    }

    function addAutoExpand(field) {
        field.addEventListener('input', function () {
            autoExpand(field);
        });
        autoExpand(field);
    }

    if (materialField) addAutoExpand(materialField);
    if (descriptionField) addAutoExpand(descriptionField);
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
        const rowHeight = gridApi.getSizesForCurrentTheme().rowHeight || 28;  // Get row height from theme, fallback to 28
        const headerElement = document.querySelector('.ag-header');  // Get the header DOM element
        const headerHeight = headerElement ? headerElement.offsetHeight : 32;  // Fallback to 32 if not found

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
            calculateTotals(); // Recalculate totals after row deletion
        }
    }

    function createNewRow(gridType) {
        const companyDefaults = document.getElementById('companyDefaults');
        const defaultWageRate = parseFloat(companyDefaults.dataset.wageRate);
        const defaultChargeOutRate = parseFloat(companyDefaults.dataset.chargeOutRate);

        // console.log('defaultWageRate:', defaultWageRate);
        // console.log('defaultChargeOutRate:', defaultChargeOutRate);

        if (gridType === 'TimeTable') {
            return {
                description: '',
                items: 0,
                mins_per_item: 0,
                total_minutes: 0,
                wage_rate: defaultWageRate,
                charge_out_rate: defaultChargeOutRate,
                total: 0
            };
        } else if (gridType === 'MaterialsTable') {
            return {
                item_code: '',
                description: '',
                quantity: 0,
                cost_price: 0,
                retail_price: 0,
                total: 0,
                comments: ''
            };
        } else if (gridType === 'AdjustmentsTable') {
            return {description: '', cost_adjustment: 0, price_adjustment: 0,  comments: ''};
        }
        return {};
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
        const correctedGridType = `${gridType}Table`;  // Append 'Table' to the gridType
        return [createNewRow(correctedGridType) || {}];  // Return the result of createNewRow as an array
    }

    function calculateTotals() {
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
                        const total = parseFloat(node.data.total) || 0;
                        const totalType = gridType.toLowerCase();
                        if (totals[totalType] && totals[totalType][section] !== undefined) {
                            totals[totalType][section] += total;
                        }
                    });
                }
            });
        });

        const totalsGrid = window.grids['totalsTable'];
        if (totalsGrid && totalsGrid.api) {
            totalsGrid.api.forEachNode((node, index) => {
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
            totalsGrid.api.refreshCells();
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
                data.total = (data.total_minutes || 0) * (data.charge_out_rate / 60.0 || 0);
            } else if (gridType === 'MaterialsTable') {
                data.total = (data.quantity || 0) * (data.retail_rate || 0);
            }
            event.api.refreshCells({rowNodes: [event.node], columns: ['total', 'total_minutes'], force: true});

            debouncedAutosaveData(event);
            calculateTotals();
        }
    };

    const trashCanColumn = {
        headerName: '',
        field: '',
        width: 40,
        cellRenderer: deleteIconCellRenderer,
        onCellClicked: onDeleteIconClicked,
        cellStyle: {
            display: 'flex',           // Use Flexbox for easier alignment
            alignItems: 'center',      // Vertically center the icon
            justifyContent: 'center',  // Horizontally center the icon
            padding: 0                 // Remove any extra padding
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
            {headerName: 'Total', field: 'total', editable: false, valueFormatter: currencyFormatter},
            trashCanColumn,
        ],
        rowData: [createNewRow('TimeTable')],
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
                field: 'cost_rate',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Retail Rate',
                field: 'retail_rate',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {headerName: 'Total', field: 'total', editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Comments', field: 'comments', editable: true, flex: 2},
            trashCanColumn,
        ],
        rowData: [createNewRow('MaterialsTable')],
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
                field: 'total',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {headerName: 'Comments', field: 'comments', editable: true, flex: 2},
            trashCanColumn,
        ],
        rowData: [createNewRow('AdjustmentsTable')],
        context: {gridType: 'AdjustmentsTable'}
    };

    const sections = ['estimate', 'quote', 'reality'];
    const workType = ['Time', 'Materials', 'Adjustments'];
    window.grids = {};

    sections.forEach(section => {
        workType.forEach(gridType => {
            const gridKey = `${section}${gridType}Table`;
            const gridElement = document.querySelector(`#${gridKey}`);

            if (!gridElement) {
                console.error(`Grid element not found for ${gridKey}`);
                return;
            }

            let specificGridOptions;
            switch (gridType) {
                case 'Time':
                    specificGridOptions = timeGridOptions;
                    break;
                case 'Materials':
                    specificGridOptions = materialsGridOptions;
                    break;
                case 'Adjustments':
                    specificGridOptions = adjustmentsGridOptions;
                    break;
            }

            const rowData = createDefaultRowData(gridType);
            // console.log("Grid type: ", gridType, ", Section: ", section, ", Grid Key: ", gridKey);
            // console.log("First row of rowData during grid initialization:", rowData[0]);

            const gridOptions = {
                ...commonGridOptions,
                ...specificGridOptions,
                context: {section, gridType: `${gridType}Table`, gridKey: gridKey},
                rowData: rowData,
            };

            try {
                const gridInstance = agGrid.createGrid(gridElement, gridOptions);
                // console.log(`Grid options for ${gridKey}:`, gridOptions);
                // console.log(`Grid instance for ${gridKey}:`, gridInstance);
            } catch (error) {
                console.error(`Error initializing grid for ${gridKey}:`, error);
            }
        });
    });

    setTimeout(() => {
        const expectedGridCount = sections.length * workType.length + 1; // 3 secionds of 3 grids, plus totals
        const actualGridCount = Object.keys(window.grids).length;

        if (actualGridCount !== expectedGridCount) {
            console.error(`Not all grids were initialized. Expected: ${expectedGridCount}, Actual: ${actualGridCount}`);
        } else {
            console.log('All grids successfully initialized.');
        }
    }, 3000); // 3-second delay to allow all grids to finish initializing

    // Grid options for Totals table (default 4 rows, autoHeight for proper resizing)
    const totalsGridOptions = {
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
            window.grids['totalsTable'] = {gridInstance: params.api, api: params.api};
            params.api.sizeColumnsToFit();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        autoSizeStrategy: {
            type: 'fitCellContents'
        }
    };

    const totalsTableEl = document.querySelector('#totalsTable');
    if (totalsTableEl) {
        try {
            agGrid.createGrid(totalsTableEl, totalsGridOptions);
            // console.log('Totals table initialized:', totalsGrid);
        } catch (error) {
            console.error('Error initializing totals table:', error);
        }
    } else {
        console.error('Totals table element not found');
    }

    // Copy Estimate to Quote (stub)
    const copyEstimateButton = document.getElementById('copyEstimateToQuote');
    if (copyEstimateButton) {
        copyEstimateButton.addEventListener('click', function () {
            alert('Copy estimate feature coming soon!');
            // console.log('Copying estimate to quote');
            // Implement the actual copying logic here
        });
    }

    // Submit Quote to Client (stub)
    const submitQuoteButton = document.getElementById('submitQuoteToClient');
    if (submitQuoteButton) {
        submitQuoteButton.addEventListener('click', function () {
            alert('Submit quote feature coming soon!');
            // console.log('Submitting quote to client');
            // Implement the actual submission logic here
        });
    }

    const reviseQuoteButton = document.getElementById('reviseQuote');
    if (reviseQuoteButton) {
        reviseQuoteButton.addEventListener('click', function () {
            alert('Revise Quote feature coming soon!');
            // console.log('Revise the quote');
            // Implement the actual submission logic here
        });
    }

    const invoiceJobButton = document.getElementById('invoiceJobButton');
    if (invoiceJobButton) {
        invoiceJobButton.addEventListener('click', function () {
            alert('Invoice Job feature coming soon!');
            // console.log('Invoice Job');
            // Implement the actual invoice logic here
        });
    }

    const contactClientButton = document.getElementById('contactClientButton');
    if (contactClientButton) {
        contactClientButton.addEventListener('click', function () {
            alert('Contact Client feature coming soon!');
            // console.log('Contact Client');
            // Implement the actual contact logic here
        });
    }

    setTimeout(() => {
        // console.log('Calling initial calculateTotals');
        calculateTotals();
    }, 1000);
});
