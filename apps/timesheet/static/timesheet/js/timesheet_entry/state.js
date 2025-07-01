// - Used to track changes and compare previous vs current row states to avoid unnecessary/repeated saves
// - Persisted to localStorage to maintain state between page refreshes
export const rowStateTracker =
  JSON.parse(localStorage.getItem("rowStateTracker")) || {};

export const timesheet_data = (() => {
  try {
    const data = {
      timesheet_date: JSON.parse(
        document.getElementById("timesheet-date")?.textContent,
      ),
      jobs: JSON.parse(document.getElementById("jobs-data")?.textContent),
      time_entries: JSON.parse(
        document.getElementById("timesheet-entries-data")?.textContent,
      ),
      staff: JSON.parse(document.getElementById("staff-data")?.textContent),
    };
    return Object.values(data).every((val) => val !== null) ? data : null;
  } catch (e) {
    return null;
  }
})();
