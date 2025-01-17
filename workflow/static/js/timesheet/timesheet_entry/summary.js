import { renderMessages } from './messages.js';


/**
 * Updates the summary section with the total hours worked and compares them with scheduled hours.
 */
export function updateSummarySection() {
    const grid = window.grid;
    if (!grid) {
        console.error("Grid instance not found.");
        return;
    }

    let totalHours = 0;
    let shopHours = 0;
    let billableCount = 0;
    let nonBillableCount = 0;
    let hasInconsistencies = false;
    const jobsWithIssues = [];
    const shopEntriesLog = []; // Array to log shop entries

    // Sum all the hours in the grid
    grid.forEachNode(node => {
        const jobData = node?.data?.job_data;
        const hours = node?.data?.hours || 0;

        if (hours > 0) {
            totalHours += hours;
            node.data.is_billable ? billableCount++ : nonBillableCount++;
        }

        if (jobData && jobData.client_name === 'MSM (Shop)') {
            const previousShopHours = shopHours;
            shopHours += hours;
            shopEntriesLog.push({
                jobName: jobData.name,
                hours: hours,
                previousTotal: previousShopHours,
                newTotal: shopHours
            });
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
        <tr class="border border-black">
            <td>Shop Hours</td>
            <td>${shopHours.toFixed(1)} (${shopHours > 0 ? ((shopHours / totalHours) * 100).toFixed(1) + '%' : 'No shop hours detected'})</td>
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

    if ((shopHours / totalHours) >= 0.5) {
        renderMessages([{ level: "warning", message: "High shop time detected! More than 50% of hours are shop hours." }], 'time-entry');
    }
}
