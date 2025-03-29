/**
 * Job section handling for purchase orders
 * Following the pattern from timesheet job_section.js
 */

function getStatusIcon(status) {
    const icons = {
        quoting: "📝",
        approved: "✅",
        rejected: "❌",
        in_progress: "🚧",
        on_hold: "⏸️",
        special: "⭐",
        completed: "✔️",
        archived: "📦",
    };
    return icons[status] || "";
}

/**
 * Updates the jobs list and renders the updated section dynamically.
 * @param {Array<Object>} jobs - Jobs to be displayed.
 */
export function updateJobsList(jobs) {
    renderJobsSection(jobs);
}

/**
 * Renders the jobs section in the DOM based on the current jobs list.
 * @param {Array<Object>} currentJobs - Current list of jobs to render.
 */
function renderJobsSection(currentJobs) {
    const jobsList = document.getElementById("jobs-list");
    if (!jobsList) {
        console.error("Element #jobs-list not found in the DOM.");
        return;
    }

    jobsList.innerHTML = "";

    const jobsSection = document.getElementById("current-jobs");

    if (currentJobs.length === 0) {
        jobsList.innerHTML = `
            <div id="no-jobs-alert" class="alert alert-info text-center align-self-center w-100" role="alert">
                No jobs are currently loaded.
            </div>
        `;
        return;
    }

    // Remove any existing no-jobs alert
    const existingAlert = jobsSection.querySelector("#no-jobs-alert");
    if (existingAlert) {
        existingAlert.remove();
    }

    // Update the jobs list class based on the number of jobs
    jobsList.className =
        currentJobs.length === 1
            ? "row row-cols-1 g-3 w-100"
            : "row row-cols-1 row-cols-md-2 g-3";

    // Render cards for each job
    currentJobs.forEach((job) => {
        const jobCard = createJobItem(job, currentJobs.length === 1);
        jobsList.insertAdjacentHTML("beforeend", jobCard);
    });

    adjustJobContainerHeight();
}

/**
 * Creates a DOM element for a single job item.
 * @param {Object} job - Job data to render.
 * @param {boolean} isSingleJob - Whether this is the only job being displayed.
 * @returns {HTMLElement} - The DOM element for the job item.
 */
function createJobItem(job, isSingleJob = false) {
    const statusIcon = getStatusIcon('special'); // All jobs are 'special' as per requirements
    const materialsExceeded = job.materials_purchased > job.estimated_materials;
    const warningMessage = materialsExceeded
        ? `<small class="text-danger">⚠ Exceeds estimated materials</small>`
        : "";

    // Add w-100 class if it's a single job
    const colClass = isSingleJob ? "col w-100" : "col";
    
    // Make sure job_number and name are defined
    const jobNumber = job.job_number || '';
    const jobName = job.name || '';
    const jobDisplayName = `${jobNumber} - ${jobName}`;

    return `
        <div class="${colClass}">
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title text-truncate">
                        <a href="/job/${job.id}" class="text-decoration-none">
                            ${statusIcon} ${jobDisplayName}
                        </a>
                    </h5>
                    <p class="card-text mb-1"><strong>Status:</strong> Special</p>
                    <p class="card-text mb-1"><strong>Client:</strong> ${job.client_name || "N/A"}</p>
                    <p class="card-text mb-1"><strong>Estimated Materials:</strong> $${job.estimated_materials.toFixed(2)}</p>
                    <p class="card-text mb-1">
                        <strong>Materials Purchased:</strong> $${job.materials_purchased.toFixed(2)}
                        ${warningMessage}
                    </p>
                </div>
            </div>
        </div>
    `;
}

/**
 * Capitalizes the first letter of a string.
 * @param {string} str - The string to capitalize.
 * @returns {string} - The capitalized string.
 */
function capitalizeFirstLetter(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function adjustJobContainerHeight() {
    const jobsContainer = document.getElementById("current-jobs");
    const jobsList = document.getElementById("jobs-list");
    const summarySection = document.getElementById("summary-section");

    if (!jobsContainer || !jobsList || !summarySection) return;

    const jobsContentHeight = jobsList.scrollHeight;

    if (jobsContentHeight > summarySection.offsetHeight) {
        jobsContainer.style.height = `${jobsContentHeight}px`;
    } else {
        jobsContainer.style.height = `${summarySection.offsetHeight}px`;
    }
}