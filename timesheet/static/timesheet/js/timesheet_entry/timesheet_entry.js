import {
  triggerAutoCalculationForAllRows,
  createNewRow,
  initializeGrid,
  adjustGridHeight,
} from "./grid_manager.js";
import { gridOptions, checkExistingShopJobs } from "./grid.js";
import { getCookie } from "./utils.js";
import { timesheet_data, rowStateTracker } from "./state.js";
import { fetchJobs } from "./job_section.js";
import { updateSummarySection } from "./summary.js";

window.timesheet_data = timesheet_data;
const csrftoken = getCookie("csrftoken");

const gridDiv = document.querySelector("#timesheet-grid");
initializeGrid(gridDiv, {
  ...gridOptions,
  domLayout: "autoHeight",
});

document.addEventListener("DOMContentLoaded", function () {
  fetchJobs();

  // Initialize rowStateTracker from localStorage or create a new one
  if (!localStorage.getItem("rowStateTracker")) {
    window.grid.addEventListener("firstDataRendered", () => {
      console.log("Grid data has been rendered. Initializing rowStateTracker.");

      const nodes = [];
      window.grid.forEachNode((node) => {
        nodes.push(node);
      });

      console.log("Grid nodes:", nodes);

      nodes.forEach((node) => {
        if (node.data && node.data.id) {
          rowStateTracker[node.id] = { ...node.data };
        }
      });

      localStorage.setItem("rowStateTracker", JSON.stringify(rowStateTracker));
      console.log("Initial row state saved: ", rowStateTracker);

      // Update summary after the first data is rendered
      adjustGridHeight();
      updateSummarySection();
    });
  } else {
    console.log("Loaded rowStateTracker from localStorage.");
    Object.assign(
      rowStateTracker,
      JSON.parse(localStorage.getItem("rowStateTracker")),
    );
    console.log("RowStateTracker: ", rowStateTracker);
  }

  // Apply initial data to the grid
  if (window.timesheet_data.time_entries?.length > 0) {
    console.log('Timesheet data: ', window.timesheet_data);
    window.grid.applyTransaction({ add: window.timesheet_data.time_entries });
    triggerAutoCalculationForAllRows();

    // Check existing jobs to mark Shop Jobs
    checkExistingShopJobs();
  } else {
    window.grid.applyTransaction({
      add: [createNewRow()],
    });
  }

  adjustGridHeight();
  updateSummarySection();

  // Attach event listeners to the grid for dynamic updates
  window.grid.addEventListener("rowDataUpdated", updateSummarySection);
  window.grid.addEventListener("rowDataChanged", updateSummarySection);
  window.grid.addEventListener("cellValueChanged", updateSummarySection);

  $.ajaxSetup({
    beforeSend: function (xhr, settings) {
      if (!this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      }
    },
  });
});
