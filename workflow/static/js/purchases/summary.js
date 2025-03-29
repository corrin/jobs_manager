import { renderMessages } from "./messages.js";

/**
 * Updates the summary section with the total materials cost and highlights any jobs
 * where materials cost exceeds the estimated cost.
 */
export function updateSummarySection() {
    const grid = window.grid;
    if (!grid) {
        console.error("Grid instance not found.");
        return;
    }

    let totalMaterialsCost = 0;
    let jobsWithIssues = [];
    let jobMaterialsMap = new Map(); // Map to track materials cost per job

    // Iterate through grid rows to calculate summary data
    grid.forEachNode((node) => {
        const jobId = node?.data?.job;
        if (!jobId) return;

        const job = window.purchaseData.jobs.find(j => j.id === jobId);
        if (!job) return;

        // Calculate cost for this line item
        const quantity = node.data.quantity || 0;
        const unitCost = node.data.unit_cost === 'TBC' ? 0 : (node.data.unit_cost || 0);
        const lineCost = quantity * unitCost;
        
        // Add to total materials cost
        totalMaterialsCost += lineCost;
        
        // Track materials cost per job
        if (!jobMaterialsMap.has(jobId)) {
            jobMaterialsMap.set(jobId, {
                job_number: job.job_number,
                name: job.name,
                estimated_materials: job.estimated_materials,
                materials_cost: 0
            });
        }
        
        jobMaterialsMap.get(jobId).materials_cost += lineCost;
        
        // Check if this job exceeds estimated materials
        if (jobMaterialsMap.get(jobId).materials_cost > job.estimated_materials) {
            const jobInfo = jobMaterialsMap.get(jobId);
            if (!jobsWithIssues.some(j => j.job_number === jobInfo.job_number)) {
                jobsWithIssues.push({
                    job_number: jobInfo.job_number,
                    name: jobInfo.name
                });
            }
        }
    });

    // Prepare the summary data
    const summaryTableBody = document.getElementById("summary-table-body");
    if (!summaryTableBody) {
        console.error("Summary table not found.");
        return;
    }

    const summaryRows = `
        <tr>
            <td>Total Materials Cost</td>
            <td>$${totalMaterialsCost.toFixed(2)}</td>
        </tr>
        <tr>
            <td>Number of Jobs</td>
            <td>${jobMaterialsMap.size}</td>
        </tr>
        ${
            jobsWithIssues.length > 0
            ? `<tr class="table-warning">
                <td>Jobs with Issues</td>
                <td>${
                    jobsWithIssues.length > 2
                    ? jobsWithIssues.slice(0, 2).map(j => j.job_number).join(", ") + `, ...`
                    : jobsWithIssues.map(j => j.job_number).join(", ")
                }</td>
            </tr>`
            : ""
        }
    `;

    // Update the table body
    summaryTableBody.innerHTML = summaryRows;

    // Render warning messages for jobs with issues
    if (jobsWithIssues.length > 0) {
        renderMessages(
            [
                {
                    level: "warning",
                    message: "Some jobs exceed estimated materials cost. Please review them.",
                },
            ],
            "purchase-order-messages",
        );
    }
}