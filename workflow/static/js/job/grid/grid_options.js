import { numberParser, currencyFormatter } from "./parsers.js";
import {
  calculateGridHeight,
  onCellKeyDown,
  calculateRetailRate,
  getRetailRate,
  setRetailRate,
  calculateTotalCost,
  calculateTotalRevenue,
  adjustGridHeight,
  fetchMaterialsMarkup
} from "./grid_utils.js";

import { debouncedAutosave } from "../edit_job_form_autosave.js";
import {
  calculateSimpleTotals,
  recalcSimpleTimeRow,
} from "./revenue_cost_options.js";

export function createCommonGridOptions() {
  return {
    rowHeight: 28,
    headerHeight: 32,
    suppressPaginationPanel: true,
    suppressHorizontalScroll: true,
    defaultColDef: {
      sortable: true,
      resizable: true,
    },
    onGridReady: function (params) {
      // Store the grid API in the global window.grids object for easy access
      const gridKey = params.context.gridKey; // Using the context to uniquely identify the grid
      const gridElement = document.querySelector(`#${gridKey}`);
      const initialNumRows = 1; // Default initial number of rows
      const initialGridHeight = calculateGridHeight(params.api, initialNumRows);
      gridElement.style.height = `${initialGridHeight}px`;

      window.grids[gridKey] = { api: params.api };

      const rowCount = params.api.getDisplayedRowCount() || 1;
      if (rowCount < 13) {
        gridElement.classList.add('ag-rows-few');
        gridElement.classList.remove('ag-rows-many');
      } else {
        gridElement.classList.add('ag-rows-many');
        gridElement.classList.remove('ag-rows-few');
      }

      // This avoids warning in case the grid is hidden (d-none)
      if (gridElement && gridElement.offsetWidth > 0) {
        params.api.sizeColumnsToFit();
      }
      adjustGridHeight(params.api, `${gridKey}`);
      calculateSimpleTotals();
    },
    onGridSizeChanged: (params) => {
      const gridKey = params.context.gridKey;
      const gridElement = document.querySelector(`#${gridKey}`);
      
      const rowCount = params.api.getDisplayedRowCount();
      if (rowCount < 13) {
        gridElement.classList.add('ag-rows-few');
        gridElement.classList.remove('ag-rows-many');
      } else {
        gridElement.classList.add('ag-rows-many');
        gridElement.classList.remove('ag-rows-few');
      }
      
      if (gridElement && gridElement.offsetWidth > 0) {
        params.api.sizeColumnsToFit();
      }
      adjustGridHeight(params.api, `${gridKey}`);
    },
    enterNavigatesVertically: true,
    enterNavigatesVerticallyAfterEdit: true,
    stopEditingWhenCellsLoseFocus: true,
    tabToNextCell: (params) => {
      const allColumns = params.api.getAllDisplayedColumns();

      // Filter only "leaf columns" (real cells) - i.e., those that don't have children
      const displayedColumns = allColumns.filter(
        (col) => !col.getColDef().children,
      );

      const rowCount = params.api.getDisplayedRowCount();
      let { rowIndex, column, floating } = params.previousCellPosition;

      // If focus came from header, force start at first body row
      if (floating) {
        rowIndex = 0;
      }

      // Find current column index within filtered array
      let currentColIndex = displayedColumns.findIndex(
        (col) => col.getColId() === column.getColId(),
      );
      if (currentColIndex === -1) return null;

      let nextColIndex = currentColIndex;
      let nextRowIndex = rowIndex;

      // Total number of cells to avoid infinite loop
      const totalCells = rowCount * displayedColumns.length;
      let count = 0;

      // Helper function to test if a cell is editable,
      // providing expected parameters for isCellEditable
      function isEditable(rowIndex, colIndex) {
        // Get rowNode for current row (assuming client-side rowModel)
        const rowNode = params.api.getDisplayedRowAtIndex(rowIndex);
        const col = displayedColumns[colIndex];

        // Build parameters object for isCellEditable
        const cellParams = {
          node: rowNode,
          column: col,
          colDef: col.getColDef(),
          rowIndex: rowIndex,
          data: rowNode ? rowNode.data : null,
          api: params.api,
          context: params.context,
        };

        return col.isCellEditable(cellParams);
      }

      // Search for next editable column
      do {
        nextColIndex++; // Advance to next column
        if (nextColIndex >= displayedColumns.length) {
          // If past last column, return to first and advance row
          nextColIndex = 0;
          nextRowIndex++;
          // If we reached end of rows, return null to avoid invalid index
          if (nextRowIndex >= rowCount) {
            return null;
          }
        }
        count++;
        if (count > totalCells) {
          return null; // Avoid infinite loop if no cell is editable
        }
      } while (!isEditable(nextRowIndex, nextColIndex));

      // Ensure row is visible (automatic scroll)
      params.api.ensureIndexVisible(nextRowIndex);

      return {
        rowIndex: nextRowIndex,
        column: displayedColumns[nextColIndex],
        floating: null,
      };
    },
    onCellKeyDown: onCellKeyDown,
    onRowDataUpdated: function (params) {
      // Handles row updates
      const gridKey = params.context.gridKey;
      const gridElement = document.querySelector(`#${gridKey}`);
      const rowCount = params.api.getDisplayedRowCount();

      if (rowCount < 13) {
        gridElement.classList.add('ag-rows-few');
        gridElement.classList.remove('ag-rows-many');
      } else {
        gridElement.classList.add('ag-rows-many');
        gridElement.classList.remove('ag-rows-few');
      }
      
      const newHeight = calculateGridHeight(params.api, rowCount);
      gridElement.style.height = `${newHeight}px`;
      adjustGridHeight(params.api, `${gridKey}`);
    },
    onCellValueChanged: function (event) {
      const gridKey = event.context.gridKey;
      const gridType = event.context.gridType;
      const data = event.data;
      
      // Check row count and add helper classes to avoid overflow
      const gridElement = document.querySelector(`#${gridKey}`);
      const rowCount = event.api.getDisplayedRowCount();
      if (rowCount < 13) {
        gridElement.classList.add('ag-rows-few');
        gridElement.classList.remove('ag-rows-many');
      } else {
        gridElement.classList.add('ag-rows-many');
        gridElement.classList.remove('ag-rows-few');
      }

      switch (gridType) {
        case "TimeTable":
          if (["mins_per_item", "items"].includes(event.column.colId)) {
            const totalMinutes = event.data.items * event.data.mins_per_item;
            const hours = (totalMinutes / 60).toFixed(1);
            event.data.total_minutes = `${totalMinutes} (${hours} hours)`;
            event.api.refreshCells({
              rowNodes: [event.node],
              columns: ["total_minutes"],
              force: true,
            });
          }
          break;

        case "MaterialsTable":
          if (event.column.colId === "unit_cost") {
            fetchMaterialsMarkup(data).then((markupRate) => {
              data.unit_revenue = calculateRetailRate(
                data.unit_cost,
                markupRate,
              );
              event.api.refreshCells({
                rowNodes: [event.node],
                columns: ["unit_revenue"],
                force: true,
              });
            });
          }

          data.revenue = (data.quantity || 0) * (data.unit_revenue || 0);
          event.api.refreshCells({
            rowNodes: [event.node],
            columns: ["revenue"],
            force: true,
          });
          break;

        case "SimpleTimeTable":
          recalcSimpleTimeRow(event.data);
          event.api.refreshCells({
            rowNodes: [event.node],
            columns: ["cost_of_time", "value_of_time"],
            force: true,
          });
          calculateSimpleTotals();
          break;

        case "SimpleMaterialsTable":
          if (event.column.colId === "material_cost" && !data.isManualOverride) {
            fetchMaterialsMarkup(data).then((markupRate) => {
              const cost = parseFloat(data.material_cost) || 0;
              data.retail_price = calculateRetailRate(cost, markupRate);
              event.api.refreshCells({
                rowNodes: [event.node],
                columns: ["retail_price"],
                force: true,
              });
              calculateSimpleTotals();
            });
          }

          if (event.column.colId === "retail_price") {
            const cost = parseFloat(data.material_cost) || 0;
            const retail = parseFloat(data.retail_price) || 0;

            fetchMaterialsMarkup(data).then((markupRate) => {
              const calculatedRetail = calculateRetailRate(cost, markupRate);
              if (retail !== calculatedRetail) {
                data.isManualOverride = true;
              } else {
                data.isManualOverride = false;
              }
              calculateSimpleTotals();
            });
          }
          break;

        case "SimpleAdjustmentsTable":
          if (event.column.colId === "cost_adjustment" && !data.isManualOverride) {
            fetchMaterialsMarkup(data).then((markupRate) => {
              const cost = parseFloat(data.cost_adjustment) || 0;
              data.price_adjustment = calculateRetailRate(cost, markupRate);
              event.api.refreshCells({
                rowNodes: [event.node],
                columns: ["price_adjustment"],
                force: true,
              });
              calculateSimpleTotals();
            });
          }

          if (event.column.colId === "price_adjustment") {
            const cost = parseFloat(data.cost_adjustment) || 0;
            const retail = parseFloat(data.price_adjustment) || 0;

            fetchMaterialsMarkup(data).then((markupRate) => {
              const calculatedRetail = calculateRetailRate(cost, markupRate);
              if (retail !== calculatedRetail) {
                data.isManualOverride = true;
              } else {
                data.isManualOverride = false;
              }
              calculateSimpleTotals();
            });
          }
      }

      event.api.refreshCells({
        rowNodes: [event.node],
        columns: ["revenue", "total_minutes"],
        force: true,
      });

      adjustGridHeight(event.api, `${gridKey}`);
      debouncedAutosave(event);
      calculateTotalRevenue();
      calculateTotalCost();
      calculateSimpleTotals();
    },
  };
}

/**
 * @description Creates a base commonGridOptions object for a "Simple Totals" table.
 * @param {string} gridKey - The unique key to store the grid API in window.grids
 * @returns {Object} The common grid options
 */
export function createSimpleTotalsCommonGridOptions(gridKey) {
  return {
    rowHeight: 28,
    headerHeight: 32,
    onGridReady: (params) => {
      window.grids[gridKey] = { api: params.api };

      params.api.sizeColumnsToFit();
      calculateSimpleTotals();
    },

    onGridSizeChanged: (params) => {
      params.api.sizeColumnsToFit();
    },
  };
}

// Advanced grids
export function createAdvancedTimeGridOptions(
  commonGridOptions,
  trashCanColumn,
) {
  const enhancedTrashColumn = {
    ...trashCanColumn,
    width: 80,
    minWidth: 80,
    maxWidth: 80,
    flex: 0,
    suppressSizeToFit: true,
  };

  return {
    ...commonGridOptions,
    columnDefs: [
      {
        headerName: "Time Description",
        field: "description",
        editable: true,
        flex: 2,
        minWidth: 100,
        cellRenderer: (params) => {
          return `<span>${params.value || "No Description"}</span>`;
        },
      },
      {
        headerName: "Timesheet",
        field: "link",
        width: 120,
        minWidth: 100,
        cellRenderer: (params) => {
          if (params.data.link && params.data.link.trim()) {
            const linkLabel =
              params.data.link === "/timesheets/overview/"
                ? ""
                : "View Timesheet";

            if (linkLabel === "") {
              return `<span class="text-warning">Not found for this entry.</span>`;
            }
            return `<a href='${params.data.link}' target='_blank' class='action-link'>${linkLabel}</a>`;
          }
          return "Not found for this entry.";
        },
      },
      {
        headerName: "Items",
        field: "items",
        editable: true,
        valueParser: numberParser,
        minWidth: 80,
        flex: 1,
      },
      {
        headerName: "Mins/Item",
        field: "mins_per_item",
        editable: true,
        valueParser: numberParser,
        minWidth: 90,
        flex: 1,
      },
      {
        headerName: "Total Minutes",
        field: "total_minutes",
        editable: false,
        valueFormatter: (params) => {
          if (params.value !== undefined && params.value !== null) {
            const totalMinutes = parseFloat(params.value) || 0;
            const decimalHours = (totalMinutes / 60).toFixed(1);
            return `${totalMinutes} (${decimalHours} hours)`;
          }
          return "0 (0.0 hours)";
        },
        valueParser: (params) => {
          return parseFloat(params.newValue) || 0;
        },
      },
      {
        headerName: "Wage Rate",
        field: "wage_rate",
        editable: false,
        hide: true,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 100,
        flex: 1,
      },
      {
        headerName: "Charge Rate",
        field: "charge_out_rate",
        editable: false,
        hide: true,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 100,
        flex: 1,
      },

      {
        ...enhancedTrashColumn,
        minWidth: 120,
        flex: 1
      },
    ],
    rowData: [],
    context: { gridType: "TimeTable" },
  };
}

export function createAdvancedMaterialsGridOptions(
  commonGridOptions,
  trashCanColumn,
) {
  const enhancedTrashColumn = {
    ...trashCanColumn,
    width: 80,
    minWidth: 80,
    maxWidth: 80,
    flex: 0,
    suppressSizeToFit: true,
  };

  return {
    ...commonGridOptions,
    columnDefs: [
      {
        headerName: "Item Code",
        field: "item_code",
        editable: false,
        hide: true,
      },
      {
        headerName: "Material Description",
        field: "description",
        editable: true,
        flex: 2,
        maxWidth: 335,
        cellRenderer: (params) => {
          const description = params.value || "No Description";
          if (params.data && params.data.po_url) {
            // If po_url exists, render as a link opening in a new tab
            return `<a href="${params.data.po_url}" target="_blank" class="action-link">${description}</a>`;
          }
          // Otherwise, just render the text
          return description;
        }
      },
      {
        headerName: "Qtd.",
        field: "quantity",
        editable: true,
        maxWidth: 150,
        valueParser: numberParser,
      },
      {
        headerName: "Cost Rate",
        field: "unit_cost",
        editable: true,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
        width: 350,
        flex: 1
      },
      {
        headerName: "Retail Rate",
        field: "unit_revenue",
        editable: true,
        valueGetter: getRetailRate,
        valueSetter: setRetailRate,
        valueFormatter: currencyFormatter,
        minWidth: 80,
        width: 190,
        flex: 1
      },
      {
        headerName: "Revenue",
        field: "revenue",
        editable: false,
        hide: true,
        valueFormatter: currencyFormatter,
      },
      {
        headerName: "Comments",
        field: "comments",
        editable: true,
        flex: 2,
        width: 150
      },
      enhancedTrashColumn,
    ],
    rowData: [],
    context: { gridType: "MaterialsTable" },
  };
}

export function createAdvancedAdjustmentsGridOptions(
  commonGridOptions,
  trashCanColumn,
) {
  const enhancedTrashColumn = {
    ...trashCanColumn,
    width: 80,
    minWidth: 80,
    maxWidth: 80,
    flex: 0,
    suppressSizeToFit: true,
  };

  return {
    ...commonGridOptions,
    columnDefs: [
      {
        headerName: "Adjustment Description",
        field: "description",
        editable: true,
        flex: 2,
        minWidth: 395
      },
      {
        headerName: "Cost Adjustment",
        field: "cost_adjustment",
        editable: true,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
        width: 425,
        flex: 1,
      },
      {
        headerName: "Price Adjustment",
        field: "price_adjustment",
        editable: true,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
        width: 230,
        flex: 1
      },
      {
        headerName: "Comments",
        field: "comments",
        editable: true,
        flex: 2,
        width: 175
      },
      enhancedTrashColumn,
    ],
    rowData: [],
    context: { gridType: "AdjustmentTable" },
  };
}

// Simple grids
export function createSimpleTimeGridOptions(commonGridOptions, trashCanColumn) {
  const enhancedTrashColumn = {
    ...trashCanColumn,
    width: 80,
    minWidth: 80,
    maxWidth: 80,
    flex: 0,
    suppressSizeToFit: true,
    hide: true
  };

  return {
    ...commonGridOptions,
    columnDefs: [
      {
        headerName: "Time",
        field: "description",
        editable: false,
        flex: 2,
        maxWidth: 155,
        width: 155
      },
      {
        headerName: "Hours",
        field: "hours",
        editable: true,
        valueParser: numberParser,
        maxWidth: 235,
        width: 235,
      },
      {
        headerName: "Cost ($)",
        field: "cost_of_time",
        editable: false,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
      },
      {
        headerName: "Retail ($)",
        field: "value_of_time",
        editable: false,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
        width: 230
      },
      // This is needed to send data in a proper way to be saved in back-end
      {
        headerName: "Wage Rate",
        field: "wage_rate",
        editable: false,
        hide: true,
      },
      {
        headerName: "Charge Rate",
        field: "charge_out_rate",
        editable: false,
        hide: true,
      },
      enhancedTrashColumn,
    ],
    context: { gridType: "SimpleTimeTable" },
  };
}

export function createSimpleMaterialsGridOptions(
  commonGridOptions,
  trashCanColumn,
) {
  const enhancedTrashColumn = {
    ...trashCanColumn,
    width: 80,
    minWidth: 80,
    maxWidth: 80,
    flex: 0,
    suppressSizeToFit: true,
    hide: true
  };

  return {
    ...commonGridOptions,
    columnDefs: [
      {
        headerName: "Materials",
        field: "description",
        editable: false, // Keep editable as false for simple view
        flex: 2,
        maxWidth: 390,
        cellRenderer: (params) => {
          const description = params.value || "No Description";
          if (params.data && params.data.po_url) {
            // If po_url exists, render as a link opening in a new tab
            return `<a href="${params.data.po_url}" target="_blank" class="action-link">${description}</a>`;
          }
          // Otherwise, just render the text
          return description;
        }
      },
      {
        headerName: "Cost ($)",
        field: "material_cost",
        editable: true,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
      },
      {
        headerName: "Retail ($)",
        field: "retail_price",
        editable: true,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
        width: 230
      },
      enhancedTrashColumn,
    ],
    context: { gridType: "SimpleMaterialsTable" },
  };
}

export function createSimpleAdjustmentsGridOptions(
  commonGridOptions,
  trashCanColumn,
) {
  const enhancedTrashColumn = {
    ...trashCanColumn,
    width: 80,
    minWidth: 80,
    maxWidth: 80,
    flex: 0,
    suppressSizeToFit: true,
    hide: true
  };

  return {
    ...commonGridOptions,
    columnDefs: [
      {
        headerName: "Adjustments",
        field: "description",
        editable: false,
        flex: 2,
        maxWidth: 390
      },
      {
        headerName: "Cost ($)",
        field: "cost_adjustment",
        editable: true,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
      },
      {
        headerName: "Retail ($)",
        field: "price_adjustment",
        editable: true,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
        width: 230
      },
      enhancedTrashColumn,
    ],
    context: { gridType: "SimpleAdjustmentsTable" },
  };
}

export function createSimpleTotalsGridOptions(gridKey) {
  const commonGridOptions = createSimpleTotalsCommonGridOptions(gridKey);

  return {
    ...commonGridOptions,
    columnDefs: [
      {
        headerName: "Totals",
        field: "section",
        editable: false,
        maxWidth: 395,
      },
      {
        headerName: "Total Cost ($)",
        field: "cost",
        editable: false,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        maxWidth: 400,
      },
      {
        headerName: "Total Retail ($)",
        field: "retail",
        editable: false,
        valueParser: numberParser,
        valueFormatter: currencyFormatter,
        minWidth: 80,
        cellStyle: { "text-align": "start" }
      },
    ],
    rowData: [{ cost: 0, retail: 0 }],
    context: { gridType: "SimpleTotalTable" },
  };
}
