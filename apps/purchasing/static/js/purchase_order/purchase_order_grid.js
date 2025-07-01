/**
 * Purchase Order Grid Management
 *
 * Handles AG Grid initialization and management
 */

import { ActiveJobCellEditor } from "./job_cell_editor.js";
import { renderMessages } from "./messages.js";
import {
  getState,
  updateState,
  getStatusDisplay,
} from "./purchase_order_state.js";
import {
  debouncedAutosave,
  markLineItemAsDeleted,
} from "./purchase_order_autosave.js";
import { updateJobSummary } from "./purchase_order_summary.js";
import { fetchMetalTypes } from "./purchase_order_metal_types.js";

/**
 * Create a new empty row for the grid
 * @returns {Object} Empty row data
 */
export function createNewRow() {
  return {
    id: crypto.randomUUID(), // Use 'id' to match backend
    job: "",
    description: "",
    quantity: 1,
    unit_cost: null,
    price_tbc: false,
    metal_type: "unspecified", // Default value from MetalType enum
    alloy: "",
    specifics: "",
    location: "",
    dimensions: "",
    supplier_item_code: "",
  };
}

/**
 * Adjust grid height based on number of rows
 */
export function adjustGridHeight() {
  const state = getState();
  const gridElement = document.getElementById("purchase-order-lines-grid");
  if (!gridElement || !state.grid || !state.grid.api) return;

  // Count rows and calculate appropriate height
  let rowCount = 0;
  state.grid.api.forEachNode(() => rowCount++);

  // Use the consistent dimensions from our unified grid styles
  const rowHeight = 28;
  const headerHeight = 32;
  const padding = 5;
  const minHeight = 500;

  // Maximum height with scrolling beyond this point (same as timesheet)
  const maxVisibleRows = 10; // Show up to 10 rows before scrolling
  const maxHeight = Math.min(
    Math.max(rowCount * rowHeight + headerHeight + padding, minHeight),
    maxVisibleRows * rowHeight + headerHeight + padding,
  );

  // Set max height instead of fixed height to enable scrolling
  gridElement.style.maxHeight = `${maxHeight}px`;

  // Ensure the grid has proper overflow settings
  gridElement.style.overflowY = "auto";
}

/**
 * Create a new row and add it to the grid
 * @param {Object} api - AG Grid API
 */
export function createNewRowShortcut(api) {
  const state = getState();

  // Check if purchase order is in draft status
  if (
    state.purchaseData.purchaseOrder &&
    state.purchaseData.purchaseOrder.status &&
    state.purchaseData.purchaseOrder.status !== "draft"
  ) {
    // Show message that rows cannot be added
    renderMessages(
      [
        {
          level: "error",
          message: `Cannot add new items. This purchase order is in ${getStatusDisplay(state.purchaseData.purchaseOrder.status)} status.`,
        },
      ],
      "purchase-order",
    );
    return;
  }

  // Add the new row
  const result = api.applyTransaction({
    add: [createNewRow()],
  });

  // Assert the row was added successfully
  console.assert(
    result && result.add && result.add.length === 1,
    "Failed to add new row",
  );

  // Focus the first cell of the new row
  setTimeout(() => {
    const lastRowIndex = api.getDisplayedRowCount() - 1;
    api.setFocusedCell(lastRowIndex, "job");
    adjustGridHeight();
  }, 100);
}

/**
 * Delete a row from the grid
 * @param {Object} api - AG Grid API
 * @param {Object} node - Row node
 */
export function deleteRow(api, node) {
  const state = getState();

  // Check if purchase order is in draft status
  if (
    state.purchaseData.purchaseOrder &&
    state.purchaseData.purchaseOrder.status &&
    state.purchaseData.purchaseOrder.status !== "draft"
  ) {
    // Show message that rows cannot be deleted
    renderMessages(
      [
        {
          level: "error",
          message: `Cannot delete items. This purchase order is in ${getStatusDisplay(state.purchaseData.purchaseOrder.status)} status.`,
        },
      ],
      "purchase-order",
    );
    return;
  }

  // Only delete if there's more than one row
  if (api.getDisplayedRowCount() > 1) {
    // If the row has a row_id, mark it for deletion on the server
    if (node.data.row_id) {
      markLineItemAsDeleted(node.data.row_id);
    }

    // Delete the row
    const result = api.applyTransaction({ remove: [node.data] });
    console.assert(
      result && result.remove && result.remove.length === 1,
      "Failed to remove row",
    );

    adjustGridHeight();
    updateJobSummary();
    debouncedAutosave().then((success) => {
      updateState({ lastAutosaveSuccess: success });
    });
  }
}

/**
 * Cell value change handler for the grid
 * @param {Object} params - Cell value changed event params
 */
function onCellValueChanged(params) {
  const state = getState();

  // If this is the last row and contains data, add a new empty row
  const isLastRow =
    params.node.rowIndex === params.api.getDisplayedRowCount() - 1;
  const hasData =
    params.data.job ||
    params.data.description ||
    params.data.quantity !== "" ||
    params.data.unit_cost !== "";

  // Only add a new row if the purchase order is in draft status
  const isDraft =
    !state.purchaseData.purchaseOrder ||
    !state.purchaseData.purchaseOrder.status ||
    state.purchaseData.purchaseOrder.status === "draft";

  if (isLastRow && hasData && isDraft) {
    createNewRowShortcut(params.api);
  }

  // Determine which cells to refresh based on what changed
  const jobId = params.data.job;
  const changedField = params.colDef.field;
  const isCostRelatedChange = [
    "job",
    "quantity",
    "unit_cost",
    "price_tbc",
  ].includes(changedField);

  if (jobId && isCostRelatedChange) {
    // Find all nodes with this job
    const nodesToRefresh = [];
    params.api.forEachNode((node) => {
      if (node.data.job === jobId) {
        nodesToRefresh.push(node);
      }
    });

    // Refresh total cells for all related job rows
    params.api.refreshCells({
      rowNodes: nodesToRefresh,
      columns: ["total"],
      force: true,
    });

    // Check if materials cost exceeds estimated cost
    const job = state.purchaseData.jobs.find((j) => j.id === jobId);
    if (job) {
      // Calculate total cost for this job from all rows
      let jobTotal = 0;
      params.api.forEachNode((node) => {
        if (
          node.data.job === jobId &&
          !node.data.price_tbc &&
          node.data.unit_cost !== null
        ) {
          jobTotal += node.data.quantity * node.data.unit_cost;
        }
      });

      // Show warning if cost exceeds estimate
      if (jobTotal > job.estimated_materials) {
        renderMessages(
          [
            {
              level: "warning",
              message: `Materials cost $${jobTotal.toFixed(2)} exceeds estimated $${job.estimated_materials.toFixed(2)}.`,
            },
          ],
          "purchase-order",
        );
      }
    }
  } else {
    // Update only this row's total
    params.api.refreshCells({
      rowNodes: [params.node],
      columns: ["total"],
      force: true,
    });
  }

  // Update job summary section
  updateJobSummary();

  adjustGridHeight();
  debouncedAutosave().then((success) => {
    updateState({ lastAutosaveSuccess: success });
  });
}

/**
 * Configure metal type column with improved display
 * @param {Array} options - Metal type options with value and label
 * @param {Object} columnDef - Column definition
 */
export function configureMetalTypeColumn(options, columnDef) {
  columnDef.cellEditorParams = {
    values: options.map((opt) => opt.value),
    valueFormatter: (params) => {
      const option = options.find((opt) => opt.value === params.value);
      return option ? option.label : params.value;
    },
    cellRenderer: "agSelectCellRenderer",
    cellClass: "metal-type-cell",
  };

  columnDef.valueFormatter = (params) => {
    if (!params.value) return "";
    const option = options.find((opt) => opt.value === params.value);
    return option ? option.label : params.value;
  };
}

/**
 * Initialize the AG Grid component
 * @returns {Promise} Promise resolving when grid is initialized
 */
export function initializeGrid() {
  // Initialize grid only if we have the container
  const gridDiv = document.querySelector("#purchase-order-lines-grid");
  if (!gridDiv) {
    console.error("Grid container not found");
    return Promise.reject(new Error("Grid container not found"));
  }

  const state = getState();

  // Define column definitions
  const columnDefs = [
    {
      headerName: "ID",
      field: "row_id",
      hide: true, // Hidden column for internal tracking
      suppressColumnsToolPanel: true,
    },
    {
      headerName: "Job",
      field: "job",
      editable: true,
      cellEditor: ActiveJobCellEditor,
      flex: 2,
      minWidth: 150,
      autoHeight: true,
      wrapText: true,
      valueFormatter: (params) => {
        // Just display the job_display_name that's already in the data
        return params.data?.job_display_name || "";
      },
      cellStyle: {
        "white-space": "normal",
        "line-height": "1.2",
      },
    },
    {
      headerName: "Description",
      field: "description",
      editable: true,
      flex: 3,
      minWidth: 200,
      autoHeight: true,
      wrapText: true,
      cellStyle: {
        "white-space": "normal",
        "line-height": "1.2",
      },
    },
    {
      headerName: "Metal Type",
      field: "metal_type",
      editable: true,
      cellEditor: "agSelectCellEditor",
      cellEditorParams: {
        values: state.metalTypeValues,
      },
      width: 90,
      maxWidth: 90,
    },
    {
      headerName: "Alloy",
      field: "alloy",
      editable: true,
      width: 70,
      maxWidth: 70,
    },
    {
      headerName: "Specifics",
      field: "specifics",
      editable: true,
      width: 90,
      maxWidth: 90,
    },
    {
      headerName: "Supplier Item Code",
      field: "supplier_item_code",
      editable: true,
      width: 100,
      maxWidth: 100,
    },
    {
      headerName: "Location",
      field: "location",
      editable: true,
      width: 80,
      maxWidth: 80,
    },
    {
      headerName: "Dimensions",
      field: "dimensions",
      editable: true,
      width: 90,
      maxWidth: 90,
    },
    {
      headerName: "Qty",
      field: "quantity",
      editable: true,
      width: 60,
      maxWidth: 60,
      valueParser: (params) => {
        if (params.newValue === "" || params.newValue === null) return 1;
        return Number(params.newValue);
      },
    },
    {
      headerName: "TBC",
      field: "price_tbc",
      width: 50,
      maxWidth: 50,
      editable: true,
      cellRenderer: (params) => {
        return `<input type="checkbox" ${params.value ? "checked" : ""} />`;
      },
      cellEditor: "agCheckboxCellEditor",
      cellEditorParams: {
        useFormatter: true,
      },
      onCellClicked: (params) => {
        // Toggle the checkbox value when clicked
        const newValue = !params.value;
        params.node.setDataValue("price_tbc", newValue);

        // If setting to true, immediately clear the unit cost
        if (newValue) {
          params.node.setDataValue("unit_cost", null);
        }

        // Refresh the unit_cost cell to update editability
        params.api.refreshCells({
          rowNodes: [params.node],
          columns: ["unit_cost", "total"],
          force: true,
        });
      },
      onCellValueChanged: (params) => {
        // When price_tbc changes, refresh the unit_cost cell to update editability
        params.api.refreshCells({
          rowNodes: [params.node],
          columns: ["unit_cost", "total"],
          force: true,
        });

        // If price_tbc is true, set unit_cost to null
        if (params.value) {
          params.node.setDataValue("unit_cost", null);
        }
      },
    },
    {
      headerName: "Unit Cost",
      field: "unit_cost",
      editable: (params) => !params.data.price_tbc, // Not editable when price_tbc is true
      valueParser: (params) => {
        if (params.data.price_tbc) return null;
        if (params.newValue === "" || params.newValue === null) return null;
        return Number(params.newValue);
      },
      valueFormatter: (params) => {
        if (params.data.price_tbc) return "TBC";
        if (params.value === null) return "";
        return `$${Number(params.value).toFixed(2)}`;
      },
      cellRenderer: (params) => {
        if (params.data.price_tbc) return `<span class="text-muted">TBC</span>`;
        if (params.value === null) return "";
        return `$${Number(params.value).toFixed(2)}`;
      },
    },
    {
      headerName: "Total",
      field: "total",
      valueGetter: (params) => {
        // Return TBC if price_tbc is true or unit_cost is null
        if (params.data.price_tbc || params.data.unit_cost === null) {
          return "TBC";
        }
        return params.data.quantity * params.data.unit_cost;
      },
      valueFormatter: (params) => {
        if (params.value === "TBC") return "TBC";
        return `$${Number(params.value).toFixed(2)}`;
      },
      cellStyle: (params) => {
        // Skip validation if job is empty (new row) or price is TBC
        if (!params.data.job || params.data.price_tbc || params.value === "TBC")
          return null;

        const jobId = params.data.job;
        const job = state.purchaseData.jobs.find((j) => j.id === jobId);
        if (!job) return null;

        // Calculate total cost for this job from all rows
        let jobTotal = 0;
        params.api.forEachNode((node) => {
          if (
            node.data.job === jobId &&
            !node.data.price_tbc &&
            node.data.unit_cost !== null
          ) {
            jobTotal += node.data.quantity * node.data.unit_cost;
          }
        });

        return jobTotal > job.estimated_materials
          ? { backgroundColor: "#fff3cd" }
          : null;
      },
      cellRenderer: (params) => {
        // If value is TBC, render it as such
        if (params.value === "TBC")
          return '<span class="text-muted">TBC</span>';

        // Format the value with currency
        const formattedValue = `$${Number(params.value).toFixed(2)}`;

        // Skip validation if job is empty (new row)
        if (!params.data.job) return formattedValue;

        const jobId = params.data.job;
        const job = state.purchaseData.jobs.find((j) => j.id === jobId);
        if (!job) return formattedValue;

        // Calculate total cost for this job from all rows
        let jobTotal = 0;
        params.api.forEachNode((node) => {
          if (
            node.data.job === jobId &&
            !node.data.price_tbc &&
            node.data.unit_cost !== null
          ) {
            jobTotal += node.data.quantity * node.data.unit_cost;
          }
        });

        return jobTotal > job.estimated_materials
          ? `<div style="background-color: #fff3cd">⚠️ ${formattedValue}</div>`
          : formattedValue;
      },
    },
    {
      headerName: "",
      field: "delete",
      width: 50,
      cellRenderer: () => `<span class="delete-icon">🗑️</span>`,
      onCellClicked: (params) => {
        deleteRow(params.api, params.node);
      },
    },
  ];

  // Create grid options
  const gridOptions = {
    columnDefs: columnDefs,
    rowData: state.purchaseData.lineItems.length
      ? state.purchaseData.lineItems
      : [createNewRow()],
    defaultColDef: {
      flex: 1,
      minWidth: 100,
      resizable: true,
    },
    onCellValueChanged: onCellValueChanged,
    domLayout: "autoHeight",
    // Handle keyboard navigation
    onCellKeyDown: (params) => {
      const { event, api, node, column } = params;
      const isLastRow =
        params.node.rowIndex === params.api.getDisplayedRowCount() - 1;
      const colId = column.getColId();

      // Handle different key combinations
      if (event.key === "Enter") {
        if (colId === "delete") {
          // Delete row when Enter is pressed in delete column
          deleteRow(api, node);
        } else if (colId === "unit_cost" && !event.shiftKey) {
          // Add new row when Enter is pressed in unit_cost column
          event.stopPropagation();
          createNewRowShortcut(api);
          return false;
        }
      } else if (
        event.key === "Tab" &&
        !event.shiftKey &&
        isLastRow &&
        colId === "unit_cost"
      ) {
        // Add new row when Tab is pressed in unit_cost column of last row
        createNewRowShortcut(api);
      }
    },
  };

  // Create the grid
  const grid = { api: agGrid.createGrid(gridDiv, gridOptions) };
  updateState({ grid });
  console.log("Grid initialized with data:", gridOptions.rowData);

  // Make functions accessible globally for external access
  window.createNewRow = createNewRow;
  window.createNewRowShortcut = createNewRowShortcut;

  // Initial adjustment
  adjustGridHeight();

  fetchMetalTypes().then((options) => {
    const metalTypeColumn = columnDefs.find(
      (col) => col.field === "metal_type",
    );
    configureMetalTypeColumn(options, metalTypeColumn);
    grid.api.setGridOption("columnDefs", columnDefs);
    grid.api.refreshCells({ columns: ["metal_type"] });
  });

  return Promise.resolve(true);
}

/**
 * Updates grid editability based on global readonly state or purchase order status
 */
export function updateGridEditability() {
  const state = getState();
  if (!state.grid || !state.grid.api) {
    console.error("Grid not initialized");
    return;
  }

  // Determine if grid should be readonly based on global state or purchase order status
  const isReadOnly =
    state.isReadOnly ||
    (state.purchaseData.purchaseOrder &&
      state.purchaseData.purchaseOrder.status &&
      state.purchaseData.purchaseOrder.status !== "draft");

  // Update column definitions to respect editable state
  const columnDefs = state.grid.api.getColumnDefs();
  columnDefs.forEach((col) => {
    if (col.field !== "total") {
      // Total is calculated, not editable
      if (col.field === "unit_cost") {
        // Special case for unit_cost which depends on price_tbc
        col.editable = (params) => !isReadOnly && !params.data.price_tbc;
      } else {
        col.editable = !isReadOnly;
      }
    }
  });

  // Set suppressClickEdit for the entire grid
  state.grid.api.setGridOption("suppressClickEdit", isReadOnly);

  // Apply updated column definitions
  state.grid.api.setGridOption("columnDefs", columnDefs);

  // Update visual appearance
  const gridContainer = document.querySelector(".ag-theme-alpine");
  if (gridContainer) {
    gridContainer.style.opacity = isReadOnly ? "0.8" : "1";
    gridContainer.style.pointerEvents = isReadOnly ? "none" : "auto";
  }

  // Display appropriate message
  if (isReadOnly) {
    const statusMessage =
      state.purchaseData.purchaseOrder &&
      state.purchaseData.purchaseOrder.status
        ? `Purchase order is in ${getStatusDisplay(state.purchaseData.purchaseOrder.status)} status.`
        : "Purchase order is in read-only mode.";

    renderMessages(
      [
        {
          level: "info",
          message: `${statusMessage} Line items cannot be edited.`,
        },
      ],
      "purchase-order",
    );
  } else {
    renderMessages(
      [
        {
          level: "success",
          message: "Purchase order is editable. You can modify the line items.",
        },
      ],
      "purchase-order",
    );
  }

  // Refresh all cells to apply the changes
  state.grid.api.refreshCells({ force: true });
}
