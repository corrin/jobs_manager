import { ActiveJobCellEditor } from "./job_cell_editor.js";
import { rowStateTracker, timesheet_data } from "./state.js";
import { currencyFormatter } from "./utils.js";
import {
  createNewRow,
  calculateAmounts,
  adjustGridHeight,
} from "./grid_manager.js";
import { updateSummarySection } from "./summary.js";
import { debouncedAutosave, markEntryAsDeleted } from "./timesheet_autosave.js";
import { renderMessages } from "./messages.js";

function deleteIconCellRenderer() {
  return `<span class="delete-icon">🗑️</span>`;
}

// Custom function to render the billable cell
function billableCellRenderer(params) {
  if (params.data?.is_shop_job) {
    return `<div class="non-billable-shop" title="Shop jobs cannot be billable" 
            style="display: flex; align-items: center; justify-content: center; 
            color: #888; cursor: not-allowed;">
            <span style="font-size: 16px">❌</span>
            </div>`;
  }

  // Renders the default checkbox for non-shop jobs
  const checked = params.value ? "checked" : "";
  return `<input type="checkbox" ${checked} class="ag-checkbox-input" />`;
}

export const gridOptions = {
  columnDefs: [
    {
      field: "id",
      hide: true, // Hidden column for the database ID
      editable: false,
    },
    {
      field: "job_number",
      headerName: "Job #",
      flex: 1,
      minWidth: 100,
      editable: true,
      cellEditor: ActiveJobCellEditor,
      cellEditorParams: {
        values: timesheet_data.jobs.map((job) => job.job_display_name),
      },
    },
    {
      field: "client_name",
      headerName: "Client",
      flex: 1.5,
      minWidth: 120,
      editable: false,
    },
    {
      field: "job_name",
      headerName: "Job Name",
      flex: 2,
      minWidth: 120,
      editable: false,
    },
    {
      field: "hours",
      headerName: "Hours",
      flex: 1,
      minWidth: 80,
      editable: true,
      type: "numericColumn",
      valueParser: (params) => Number(params.newValue),
      valueFormatter: (params) => params.value?.toFixed(2),
      cellStyle: (params) => {
        if (params.data.hours > params.data.scheduled_hours) {
          return { backgroundColor: "#fff3cd" };
        }
        return null;
      },
      cellRenderer: (params) => {
        if (params.data.hours > params.data.scheduled_hours) {
          return `<div style="background-color: #fff3cd">⚠️ ${Number(params.value).toFixed(2)}</div>`;
        }
        return Number(params.value).toFixed(2) || "";
      },
    },
    {
      field: "is_billable",
      headerName: "Billable",
      width: 60,
      editable: (params) => {
        console.log(
          "Checking if billable is editable:",
          !params.data?.is_shop_job,
        );
        return !params.data?.is_shop_job;
      },
      cellRenderer: billableCellRenderer,
    },
    {
      field: "description",
      headerName: "Description",
      flex: 2,
      minWidth: 150,
      editable: true,
    },
    {
      field: "rate_type",
      headerName: "Rate",
      flex: 1,
      minWidth: 70,
      editable: true,
      cellEditor: "agSelectCellEditor",
      cellEditorParams: {
        values: ["Ord", "1.5", "2.0", "Unpaid"],
      },
    },
    {
      field: "wage_amount",
      headerName: "Wage",
      flex: 1,
      minWidth: 80,
      editable: false,
      valueFormatter: currencyFormatter,
    },
    {
      field: "bill_amount",
      headerName: "Bill",
      flex: 1,
      minWidth: 80,
      editable: false,
      valueFormatter: currencyFormatter,
    },
    {
      field: "notes",
      editable: false,
      hide: true,
    },
    {
      field: "delete",
      headerName: "",
      width: 50,
      editable: false,
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
          const rowData = params.node.data;

          console.log("Delete clicked for row:", {
            id: rowData.id,
            rowCount: rowCount,
            data: rowData,
          });

          const isEmptyRow =
            rowData.hours <= 0 &&
            (!rowData.description?.trim() ||
              !rowData.job_number ||
              !rowData.notes);

          if (isEmptyRow) {
            console.log("Skipping empty row:", rowData);
            params.api.applyTransaction({ remove: [rowData] });
            adjustGridHeight();
            return;
          }

          if (rowData.id == null) {
            console.log("Assigning temporary ID to new row:", rowData);
            rowData.id = "tempId";
          }

          // Mark for deletion first if it has an ID
          if (rowData.id) {
            console.log("Marking entry for deletion:", rowData.id);
            markEntryAsDeleted(rowData.id);
          }

          // Then remove from grid
          params.api.applyTransaction({ remove: [rowData] });
          delete rowStateTracker[params.node.id];
          localStorage.setItem(
            "rowStateTracker",
            JSON.stringify(rowStateTracker),
          );
          console.log("Row removed from grid, triggering autosave");
          debouncedAutosave();

          if (rowCount === 1) {
            console.log("Adding a new row to keep the grid populated");
            params.api.applyTransaction({ add: [createNewRow()] });
          }

          adjustGridHeight();
          updateSummarySection();
        },
    },
    {
      field: "job_data",
      headerName: "Job Data",
      width: 0,
      hide: true, // Invisible column to make processing easier
      editable: false,
    },
    {
      field: "staff_id",
      hide: true, // Invisible column
      editable: false,
    },
    {
      field: "timesheet_date",
      hide: true, // Invisible column
      editable: false,
    },
  ],
  defaultColDef: {
    flex: 1,
    minWidth: 100,
    sortable: false,
    filter: false,
  },
  onCellValueChanged: (params) => {
    console.log("onCellValueChanged triggered:", params);

    // If job number changes, update job name, client, and job_data
    if (params.column?.colId === "job_number") {
      const job = timesheet_data.jobs.find(
        (j) => j.job_number === params.newValue,
      );

      if (!job) return;

      // Check if it's a shop job (client "MSM (Shop)")
      const isShopJob = job.client_name === "MSM (Shop)";
      console.log(
        `Job ${job.job_number} client: ${job.client_name}, isShopJob: ${isShopJob}`,
      );

      // If it's a shop job, set is_billable as false
      if (isShopJob) {
        params.node.setDataValue("is_billable", false);
        params.node.setDataValue("is_shop_job", true);
        console.log("Shop job detected - setting is_billable to false");
      } else {
        params.node.setDataValue("is_shop_job", false);
      }

      job.hours_spent += Number(params.newValue || 0);
      params.node.setDataValue("job_name", job.name);
      params.node.setDataValue("client", job.client_name);
      params.node.setDataValue("job_data", job);
      params.node.setDataValue("hours_spent", job.hours_spent);
      params.node.setDataValue("estimated_hours", job.estimated_hours);

      calculateAmounts(params.node.data);
      params.api.refreshCells({
        rowNodes: [params.node],
        force: true,
      });
    }

    // Recalculate amounts if rate type or hours changes
    if (["rate_type", "hours"].includes(params.column?.colId)) {
      params.node.setDataValue("rate_type", Number(params.newValue));
      calculateAmounts(params.node.data);
      params.api.refreshCells({
        rowNodes: [params.node],
        force: true,
      });

      // Check for hours exceeding scheduled hours
      if (params.column?.colId === "hours") {
        const totalHours = params.data.hours;
        const scheduled_hours = timesheet_data.staff.scheduled_hours;

        if (totalHours > scheduled_hours) {
          renderMessages(
            [
              {
                level: "warning",
                message: `Hours exceed scheduled (${totalHours} > ${scheduled_hours}).`,
              },
            ],
            "time-entry",
          );
          params.node.setDataValue("inconsistent", true);
        } else {
          params.node.setDataValue("inconsistent", false);
        }
        params.api.refreshCells({
          rowNodes: [params.node],
          force: true,
        });
      }
    }

    if (!(params.source === "edit")) {
      console.log("Skipping autosave - not an edit event");
      return;
    }

    debouncedAutosave();
    adjustGridHeight();
    updateSummarySection();
  },
  // Checks for the Shift + Enter shortcut, handle the creation of a new row through the Enter shortcut and check for ESC to stop editing
  onCellKeyDown: (params) => {
    const { event, api, node, column } = params;

    switch (event.key) {
      case "Escape":
        console.log("ESC pressed:", { node, column });

        // Column is not editable, skipping
        if (!column.colDef.editable) {
          return;
        }

        api.stopEditing(true);
        break;

      case "Enter":
        const isLastRow = api.getDisplayedRowCount() - 1 === params.rowIndex;

        // Shift + Enter is a different shortcut
        if (!event.shiftKey && isLastRow) {
          createNewRowShortcut(api);
        }

        // To switch the billable state of the entry through the Shift + Enter shortcut
        if (column.colId === "is_billable") {
          // Don't allow changes if it's a shop job
          if (params.data?.is_shop_job) {
            console.log("Cannot toggle billable status for shop job");
            return;
          }

          node.data.is_billable = !node.data.is_billable;
          api.refreshCells({
            rowNodes: [node],
            force: true,
          });
        }

        // To delete a row through the Shift + Enter
        if (column.colId === "deleteIcon") {
          column.colDef.onCellClicked(params);
        }

        break;
    }
  },
};

function createNewRowShortcut(api) {
  api.applyTransaction({ add: [createNewRow()] });

  // Focus the first editable cell of the newly added row
  const newRowIndex = api.getDisplayedRowCount() - 1;
  api.setFocusedCell(newRowIndex, "job_number");
  debouncedAutosave();

  console.log("Adjusting grid height");
  adjustGridHeight();
  updateSummarySection();
}

// Check during initialization if any existing job is a shop job
export function checkExistingShopJobs() {
  if (!window.grid) return;

  window.grid.forEachNode((node) => {
    if (node.data?.job_data?.client_name === "MSM (Shop)") {
      console.log("Found existing shop job, setting is_shop_job flag");
      node.setDataValue("is_shop_job", true);
      node.setDataValue("is_billable", false);
    }
  });

  window.grid.refreshCells({ force: true });
}