document.addEventListener("DOMContentLoaded", function () {
  try {
    // Fetch JSON from <script> tags
    const jobsDataElement = document.getElementById("jobs-data");
    const staffDataElement = document.getElementById("staff-data");
    const timesheetDateElement = document.getElementById("timesheet-date");
    const timesheetEntriesDataElement = document.getElementById(
      "timesheet-entries-data",
    );

    if (!jobsDataElement) {
      throw new Error("Jobs data element is missing from the DOM.");
    }
    if (!staffDataElement) {
      throw new Error("Staff data element is missing from the DOM.");
    }
    if (!timesheetDateElement) {
      throw new Error("Timesheet date data element is missing from the DOM.");
    }

    if (!timesheetEntriesDataElement) {
      throw new Error(
        "Timesheet entries data element is missing from the DOM.",
      );
    }

    // Parse JSON
    const staff = JSON.parse(staffDataElement.textContent);
    const jobs = JSON.parse(jobsDataElement.textContent);
    const timesheet_date = JSON.parse(timesheetDateElement.textContent.trim());
    const timesheetEntries = JSON.parse(
      timesheetEntriesDataElement.textContent,
    );

    // Transform timesheet entries (if needed)
    const transformedEntries = timesheetEntries.map((entry) => ({
      ...entry,
      rate_type: getRateTypeFromMultiplier(entry.rate_multiplier),
      timesheet_date: timesheet_date,
      staff_id: staff.id,
    }));

    // Expose to global scope (if needed)
    window.timesheet_data = {
      staff: staff,
      jobs: jobs,
      time_entries: transformedEntries,
      timesheet_date: timesheet_date,
    };
  } catch (error) {
    console.error("Error during deserialization or transformation:", error);
  }
});

function getRateTypeFromMultiplier(multiplier) {
  switch (multiplier) {
    case 1.5:
      return "1.5";
    case 2.0:
      return "2.0";
    default:
      return "Ord";
  }
}
