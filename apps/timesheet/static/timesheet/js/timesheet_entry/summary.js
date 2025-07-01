import { renderMessages } from "./messages.js";

/**
 * Updates the summary section with the total hours worked, billable and non-billable entries,
 * and highlights any inconsistencies in jobs.
 */
export function updateSummarySection() {
  const grid = window.grid;
  if (!grid) {
    console.error("Grid instance not found.");
    return;
  }

  let totalHours = 0;
  let billableCount = 0;
  let nonBillableCount = 0;
  let hasInconsistencies = false;
  const jobsWithIssues = [];

  // Iterate through grid rows to calculate summary data
  grid.forEachNode((node) => {
    const jobData = node?.data?.job_data;
    const hours = node?.data?.hours || 0;

    if (hours > 0) {
      totalHours += hours;
      node.data.is_billable ? billableCount++ : nonBillableCount++;
    }

    if (node?.data?.inconsistent) {
      hasInconsistencies = true;
    }

    if (jobData && jobData.hours_spent >= jobData.estimated_hours) {
      jobsWithIssues.push(jobData.name ? jobData.name : "No Job Name");
    }
  });

  // Prepare the summary data
  const scheduledHours = Number(
    window.timesheet_data.staff.scheduled_hours,
  ).toFixed(1);

  const summaryTableBody = document.getElementById("summary-table-body");
  if (!summaryTableBody) {
    console.error("Summary table not found.");
    return;
  }

  const summaryRows = `
        <tr class="table-${totalHours < scheduledHours ? "danger" : totalHours > scheduledHours ? "warning" : "success"}">
            <td>Total Hours</td>
            <td>${totalHours.toFixed(1)} / ${scheduledHours}</td>
        </tr>
        <tr>
            <td>Billable Entries</td>
            <td>${billableCount > 0 ? ((billableCount / (billableCount + nonBillableCount)) * 100).toFixed(1) + "%" : "No billable entries detected."}</td>
        </tr>
        <tr>
            <td>Non-Billable Entries</td>
            <td>${nonBillableCount > 0 ? ((nonBillableCount / (billableCount + nonBillableCount)) * 100).toFixed(1) + "%" : "No non-billable entries detected."}</td>
        </tr>
        ${
          jobsWithIssues.length > 0
            ? `<tr class="table-warning">
                <td>Jobs with Issues</td>
                <td>${
                  jobsWithIssues.length > 2
                    ? jobsWithIssues.slice(0, 2).join(", ") + `, ...`
                    : jobsWithIssues.join(", ")
                }</td>
            </tr>`
            : ""
        }
    `;

  // Update the table body
  summaryTableBody.innerHTML = summaryRows;

  // Render warning messages for inconsistencies
  if (hasInconsistencies) {
    renderMessages(
      [
        {
          level: "warning",
          message: "Some entries have inconsistencies. Please review them.",
        },
      ],
      "time-entry",
    );
  }
}
