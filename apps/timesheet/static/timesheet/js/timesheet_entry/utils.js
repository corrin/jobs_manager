import { rowStateTracker } from "./state.js";

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
export function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

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
export function getCurrentDateFromURL() {
  const urlParts = window.location.pathname.split("/").filter(Boolean);
  return urlParts[urlParts.length - 2];
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
export function hasRowChanged(previousRowData, currentRowData) {
  // Compares the row states converting them to JSON
  const hasRowChanged =
    JSON.stringify(previousRowData) !== JSON.stringify(currentRowData);
  if (!hasRowChanged) {
    console.log("No changes detected, ignoring autosave");
    return hasRowChanged;
  }
  return hasRowChanged;
}

export function currencyFormatter(params) {
  if (params.value === undefined) return "$0.00";
  return (
    "$" +
    params.value.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

/**
 * Validates if a row is valid and checks if it has been modified.
 * Updates the RowStateTracker if the row is valid.
 *
 * @param {Object} rowData - The data of the row to validate.
 * @param {string} rowId - The unique ID of the row.
 * @returns {boolean} - True if the row is valid and has been modified, otherwise false.
 */
export function validateAndTrackRow(rowData, rowId) {
  const previousRowData = rowStateTracker[rowId] || {};

  // Check if the row is valid
  const isValidRow =
    rowData.job_number &&
    rowData.hours > 0 &&
    typeof rowData.is_billable === "boolean";

  if (!isValidRow) {
    console.log("Row is invalid:", rowData);
    return false;
  }

  // Otherwise it'll fetch other data that is processed automatically on grid, even if this doesn't really means changes in the row
  const relevantFields = [
    "description",
    "hours",
    "is_billable",
    "items",
    "mins_per_item",
    "job_number",
    "rate_type",
    "notes",
    "timesheet_date",
  ];

  const filteredPrevious = relevantFields.reduce((acc, key) => {
    acc[key] =
      key === "mins_per_item"
        ? parseFloat(previousRowData[key])
        : previousRowData[key];
    return acc;
  }, {});

  const filteredCurrent = relevantFields.reduce((acc, key) => {
    acc[key] =
      key === "mins_per_item" ? parseFloat(rowData[key]) : rowData[key];
    return acc;
  }, {});

  // Comparison of previous and current states of the row, after filtering
  console.log("Previous state:", filteredPrevious);
  console.log("Current state:", filteredCurrent);
  const rowChanged =
    JSON.stringify(filteredPrevious) !== JSON.stringify(filteredCurrent);
  if (!rowChanged) {
    console.log("Row has not changed:", rowData);
    return false;
  }

  // Update the RowStateTracker
  console.log(`Row data id ${rowData} | Row node id ${rowId}`);
  rowStateTracker[rowId] = { ...rowData };
  localStorage.setItem("rowStateTracker", JSON.stringify(rowStateTracker));
  console.log("RowStateTracker updated:", rowStateTracker);

  return true;
}
