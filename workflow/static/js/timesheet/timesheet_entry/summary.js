import { renderMessages } from './messages.js';

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

    // Sum all the hours in the grid and count billable/non-billable entries
    grid.forEachNode(node => {
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
            jobsWithIssues.push(jobData.name ? jobData.name : 'No Job Name');
        }
    });

    // Update the summary table dynamically
    const scheduledHours = Number(window.timesheet_data.staff.scheduled_hours).toFixed(1);

    const summaryTableBody = document.getElementById('summary-table-body');
    if (!summaryTableBody) {
        console.error('Summary table not found');
        return;
    }

    summaryTableBody.innerHTML = `
        <tr class="border border-black ${totalHours < scheduledHours ? 'table-danger' : totalHours > scheduledHours ? 'table-warning' : 'table-success'}">
            <td>Total Hours</td>
            <td>${totalHours.toFixed(1)} / ${scheduledHours}</td>
        </tr>
        <tr class="border border-black">
            <td>Billable Entries</td>
            <td>${billableCount > 0 ? ((billableCount / (billableCount + nonBillableCount)) * 100).toFixed(1) + '%' : 'No billable entries detected.'}</td>
        </tr>
        <tr class="border border-black">
            <td>Non-Billable Entries</td>
            <td>${nonBillableCount > 0 ? ((nonBillableCount / (billableCount + nonBillableCount)) * 100).toFixed(1) + '%' : 'No non-billable entries detected.'}</td>
        </tr>
    `;

    if (jobsWithIssues.length > 0) {
        summaryTableBody.innerHTML += `
            <tr class="table-warning border border-black">
                <td>Jobs with Issues</td>
                <td>${jobsWithIssues.join(", ")}</td>
            </tr>
        `;
    }

    if (hasInconsistencies) {
        renderMessages([{ level: "warning", message: "Some entries have inconsistencies. Please review them." }], 'time-entry');
    }
}
