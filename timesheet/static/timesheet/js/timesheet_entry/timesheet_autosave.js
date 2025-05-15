import { validateAndTrackRow } from "./utils.js";
import { updateJobsList } from "./job_section.js";
import { renderMessages } from "./messages.js";
import { rowStateTracker, timesheet_data } from "./state.js";
import { updateSummarySection } from "./summary.js";
import {
  triggerAutoCalculationForAllRows,
  adjustGridHeight,
} from "./grid_manager.js";

let deletedEntries = [];

function updateGridEntries(entries) {
  const grid = window.grid;
  if (!grid) {
    console.error("Could not get grid instance");
    return;
  }

  entries.forEach((entry) => {
    grid.forEachNode((node) => {
      if (node.data.id === "tempId" && entry.id) {
        node.data.id = entry.id;
        console.log(`Replaced tempId with server ID: ${entry.id}`);
      }

      if (node.data.id === entry.id) {
        // Preserve the existing rate if not provided in the update
        const existingRate = node.data.rate_type;
        node.setData({
          ...entry,
          rate_type: entry.rate_type || existingRate || "Ord",
          mins_per_item:
            parseFloat(entry.mins_per_item) ||
            parseFloat(entry.minutes_per_item),
          items: entry.items || 0,
        });

        console.log("Updated entry:", entry);
        rowStateTracker[node.id] = { ...node.data };
      }
    });
  });

  localStorage.setItem("rowStateTracker", JSON.stringify(rowStateTracker));
  adjustGridHeight();
  grid.refreshCells({ force: true });
}

/**
 * Marks an entry as deleted for synchronization purposes.
 * This handles AG Grid's deleted rows separately from the form,
 * ensuring the backend correctly processes grid-level changes.
 */
export function markEntryAsDeleted(entryId) {
  if (entryId) {
    console.log("Adding entry to deletion list:", entryId);
    deletedEntries.push(entryId);
    console.log("Current deletion list:", deletedEntries);
  }
}

/**
 * Creates a debounced version of a function that delays its execution until after a period of inactivity.
 *
 * @param {Function} func - The function to debounce
 * @param {number} wait - The number of milliseconds to wait before executing the function
 * @returns {Function} A debounced version of the input function
 *
 * Purpose:
 * - Prevents excessive function calls (e.g., during rapid user input or frequent events)
 * - Useful for optimizing performance with autosave, search, or resize operations
 * - Only executes the function after the specified delay has passed without new calls
 *
 * Example Usage:
 * const debouncedSave = debounce(saveFunction, 1000);
 * // Will only save once, 1 second after the last call
 */
function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

/**
 * Collects and processes data from an AG Grid instance for saving.
 *
 * This function:
 * - Iterates through all rows in the grid
 * - Validates each row to ensure it has required data (hours > 0 and description/notes)
 * - Checks if row data has changed from previous state (to avoid saving data unnecessarily)
 * - Formats valid rows into entry objects with required fields
 * - Tracks row state changes for future comparisons
 * - Combines time entries with any deleted entries
 *
 * @returns {Object} Object containing:
 *   - time_entries: Array of valid grid row entries
 *   - deleted_entries: Array of entry IDs marked for deletion
 */
function collectGridData() {
  console.log("collectGridData() called");
  const gridData = [];
  const grid = window.grid;

  if (!grid) {
    console.error("Could not get grid instance");
    return gridData;
  }

  grid.forEachNode((node) => {
    if (!node || !node.data) {
      console.log("Skipping invalid node");
      return;
    }

    console.log("Processing node:", node);
    const rowData = node.data;
    const rowId = node.id;

    if (!validateAndTrackRow(rowData, rowId)) {
      console.log("Skipping invalid or unchanged row", rowData);
      return;
    }

    if (rowData.id == null) {
      rowData.id = "tempId";
    }

    const entry = {
      id: rowData.id,
      staff_id: rowData.staff_id,
      job_number: rowData.job_number,
      description: rowData.description,
      hours: rowData.hours,
      mins_per_item: rowData.mins_per_item,
      items: rowData.items,
      wage_amount: rowData.wage_amount,
      charge_out_rate: rowData.job_data?.charge_out_rate || 105.0, // Company default charge out rate
      timesheet_date: window.timesheet_data.timesheet_date,
      bill_amount: rowData.bill_amount,
      date: rowData.date,
      job_data:
        rowData.job_data ||
        timesheet_data.jobs.find(
          (job) => job.job_number === rowData.job_number,
        ),
      is_billable:
        rowData.is_billable === undefined ? true : rowData.is_billable,
      notes: rowData.notes || "",
      rate_type: rowData.rate_type || "Ord",
    };

    console.log("Entry created:", entry);

    gridData.push(entry);
  });

  console.log("Final collected data:", gridData);
  return { time_entries: gridData, deleted_entries: deletedEntries };
}

/**
 * Handles automatic saving of timesheet data to the server.
 *
 * This function collects data from the grid, filters out invalid entries,
 * and saves valid changes to the server. It only proceeds with saving if there
 * are either new/modified time entries or deleted entries to process.
 *
 * Business Logic:
 * - Only saves entries that have an ID, job number, hours and description
 * - Skips saving if there are no valid entries to update and no entries to delete
 * - Logs the number of entries being processed for debugging purposes
 */
function autosaveData() {
  const collectedData = collectGridData();

  collectedData.time_entries = collectedData.time_entries.filter(
    (entry) => entry.id && entry.job_number && entry.hours > 0,
  );

  // Changed validation - proceed if either we have entries to update or delete
  if (
    collectedData.time_entries.length === 0 &&
    collectedData.deleted_entries.length === 0
  ) {
    console.log("No data to save - no time entries or deletions");
    return;
  }

  console.log("Saving data:", {
    timeEntries: collectedData.time_entries.length,
    deletedEntries: collectedData.deleted_entries.length,
  });

  saveDataToServer(collectedData);
}

/**
 * Sends timesheet data to the server for automatic saving and handles the response.
 *
 * @param {Object} collectedData - The timesheet data to be saved.
 * @param {Array} collectedData.time_entries - Array of time entries to save/update.
 * @param {Array} collectedData.deleted_entries - Array of entries to delete.
 * @returns {Promise} Resolves when the save process is complete.
 *
 * Purpose:
 * - Automatically sync timesheet data with the server.
 * - Handle updates and deletions of entries efficiently.
 * - Maintain UI consistency by dynamically updating the grid and jobs list.
 *
 * Business Logic:
 * - Sends collected timesheet data to the server via a POST request.
 * - Updates temporary IDs (`tempId`) with permanent IDs returned by the server.
 * - Clears the `deletedEntries` list after a successful save.
 * - Updates the list of jobs (`currentJobs`) based on the server response.
 * - Displays server-provided messages (e.g., success, errors).
 *
 * Error Handling:
 * - Logs detailed error information if the save operation fails.
 * - Displays error messages returned by the server, when available.
 * - Ensures data consistency by preserving `deletedEntries` in case of errors.
 *
 * Dependencies:
 * - Requires an initialized `grid` variable for updating grid entries.
 * - Relies on `renderMessages` for displaying feedback to the user.
 * - Requires `updateJobsList` to manage the list of jobs dynamically.
 * - Requires `getCsrfToken` to provide the CSRF token for secure requests.
 *
 * Example Usage:
 * saveDataToServer({
 *   time_entries: [{ id: 'tempId', job_number: 1, hours: 4 }],
 *   deleted_entries: ['12345']
 * });
 *
 * Notes:
 * - Updates the grid nodes with permanent IDs for newly created entries.
 * - Dynamically adds or removes jobs in the UI based on the server's response.
 */
function saveDataToServer(collectedData) {
  console.log("Autosaving timesheet data to /timesheets/autosave/...", {
    time_entries: collectedData.time_entries.length,
    deleted_entries: collectedData.deleted_entries.length,
  });

  fetch("/timesheets/autosave/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify(collectedData),
  })
    .then((response) => {
      if (!response.ok) {
        console.error("Server responded with an error:", response.status);
        return response.json().then((data) => {
          console.error("Error details:", data);
          throw new Error(data.error || "Server error");
        });
      }
      console.log("Autosave successful");
      deletedEntries = [];
      return response.json();
    })
    .then((data) => {
      if (data.entry) {
        console.log("Single entry received:", data.entry);
        updateGridEntries([data.entry]);
      }

      if (data.entries) {
        console.log("Multiple entries received", data.entries);
        updateGridEntries(data.entries);
      }

      const jobs = data.jobs || [];
      const removeJobs = (data.remove_jobs || []).flat();
      if (jobs.length > 0) {
        updateJobsList(jobs, data.action, removeJobs);
      }

      deletedEntries = [];
      renderMessages(data.messages || [], "time-entry");

      console.log("Autosave successful:", data);
      triggerAutoCalculationForAllRows();
      adjustGridHeight();
      updateSummarySection();
    })
    .catch((error) => {
      console.error("Autosave failed:", error);
    });
}

// Get CSRF token for Django
export function getCsrfToken() {
  return document.querySelector("[name=csrfmiddlewaretoken]").value;
}

// Debounced autosave function
export const debouncedAutosave = debounce(autosaveData, 1500);
