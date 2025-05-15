/**
 * Filters the list of jobs to include only those related to the given time entries.
 *
 * @param {Array<Object>} jobs - The list of all jobs.
 * @param {Array<Object>} timeEntries - The list of time entries to filter against.
 * @returns {Array<Object>} The filtered list of jobs related to the time entries.
 *
 * Purpose:
 * - Ensures only jobs with matching `job_number` from the time entries are included.
 *
 * Example:
 * const jobs = [{ job_number: 1 }, { job_number: 2 }];
 * const timeEntries = [{ job_number: 1 }];
 * const filteredJobs = filterRelatedJobs(jobs, timeEntries);
 * console.log(filteredJobs); // [{ job_number: 1 }]
 */
function filterRelatedJobs(jobs, timeEntries) {
  const relatedJobNumbers = new Set(
    timeEntries.map((entry) => entry.job_number),
  );
  return jobs.filter((job) => relatedJobNumbers.has(job.job_number));
}

/**
 * Fetches jobs and time entries from the server via an AJAX request and updates the job list.
 *
 * Purpose:
 * - Retrieves data related to jobs and time entries from the backend.
 * - Filters jobs to include only those related to the time entries.
 * - Updates the job list dynamically based on the response.
 *
 * Error Handling:
 * - Logs detailed error information if the AJAX request fails.
 * - Warns if the response is missing required data (`jobs` or `time_entries`).
 *
 * Dependencies:
 * - Requires jQuery for AJAX handling.
 * - Requires `filterRelatedJobs` and `updateJobsList` functions.
 *
 * Example:
 * fetchJobs();
 */
export function fetchJobs() {
  $.ajax({
    url: window.location.pathname,
    method: "GET",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
    success: function (response) {
      if (response.jobs && response.time_entries) {
        const relatedJobs = filterRelatedJobs(
          response.jobs,
          response.time_entries,
        );

        updateJobsList(relatedJobs, "load");
      } else {
        console.warn("Jobs or time_entries missing in response.");
      }
    },
    error: function (xhr, status, error) {
      console.error(
        "Error fetching jobs:",
        error,
        "Response:",
        xhr.responseText,
      );
    },
  });
}

/**
 * Returns an emoji icon representing the job status.
 * @param {string} status - The job status.
 * @returns {string} - The emoji icon representing the status.
 */
function getStatusIcon(status) {
  const icons = {
    quoting: "📝",
    accepted_quote: "✅",  // Updated from "approved"
    awaiting_materials: "🔄", // Added missing status
    in_progress: "🚧",
    on_hold: "⏸️",
    special: "⭐",
    completed: "✔️",
    rejected: "❌",
    archived: "📦",
  };
  return icons[status] || "";
}

/**
 * Returns a human-readable display name for a job status.
 * @param {string} status - The internal job status value.
 * @returns {string} - The display name for the status.
 */
function getStatusDisplayName(status) {
  const displayNames = {
    quoting: "Quoting",
    accepted_quote: "Accepted Quote",
    awaiting_materials: "Awaiting Materials",
    in_progress: "In Progress", 
    on_hold: "On Hold",
    special: "Special",
    completed: "Completed",
    rejected: "Rejected",
    archived: "Archived"
  };
  return displayNames[status] || capitalizeFirstLetter(status);
}

/**
 * Merges new jobs into an existing jobs list or adds them if they don't exist.
 * If a job with the same ID exists, its properties are merged with the new job.
 * If a job doesn't exist, it is added to the list.
 *
 * @param {Array<Object>} jobsToProcess - Array of new jobs to be processed
 * @param {Array<Object>} currentJobsList - Array of existing jobs
 * @param {number} jobsToProcess[].id - Unique identifier for each job
 * @param {number} currentJobsList[].id - Unique identifier for each existing job
 * @returns {Array<Object>} Updated array of jobs with merged or added items
 */
function mergeOrAddJobs(jobsToProcess, currentJobsList) {
  jobsToProcess.forEach((job) => {
    const existingJobIndex = currentJobsList.findIndex(
      (currentJob) => currentJob.id === job.id,
    );
    existingJobIndex !== -1
      ? (currentJobsList[existingJobIndex] = {
          ...currentJobsList[existingJobIndex],
          ...job,
        })
      : currentJobsList.push(job);
  });
  return currentJobsList;
}

let currentJobs = [];
/**
 * Updates the jobs list and renders the updated section dynamically.
 * @param {Array<Object>} jobs - Jobs to be added or updated.
 * @param {string} action - Action type: 'load', 'add', 'remove', 'update'.
 * @param {Array<Object>} removeJobs - Jobs to be removed (for 'update' action).
 */
export function updateJobsList(jobs, action, removeJobs = []) {
  switch (action) {
    case "load":
      currentJobs = jobs; // Replace the list completely
      break;

    case "add":
      currentJobs = mergeOrAddJobs(jobs, currentJobs);
      break;

    case "remove":
      currentJobs = currentJobs.filter(
        (currentJob) => !jobs.some((job) => job.id === currentJob.id),
      );
      break;

    case "update":
      // Remove outdated jobs
      currentJobs = currentJobs.filter(
        (currentJob) => !removeJobs.some((job) => job.id === currentJob.id),
      );
      // Add or update jobs
      currentJobs = mergeOrAddJobs(jobs, currentJobs);
      break;

    default:
      console.warn(`Unknown action: ${action}`);
  }

  renderJobsSection(currentJobs);
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
    const noJobsAlert = document.createElement("div");

    noJobsAlert.id = "no-jobs-alert";
    noJobsAlert.className = "alert alert-info text-center align-self-center";
    noJobsAlert.setAttribute("role", "alert");
    noJobsAlert.textContent = "No jobs are currently loaded.";

    const titleElement = jobsSection.querySelector("h4");
    titleElement.insertAdjacentElement("afterend", noJobsAlert);

    return;
  }

  jobsSection.querySelector("#no-jobs-alert")?.remove();

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
  const statusIcon = getStatusIcon(job.job_status);
  const statusDisplayName = getStatusDisplayName(job.job_status);
  const hoursExceeded = job.hours_spent > job.estimated_hours;
  const warningMessage = hoursExceeded
    ? `<small class="text-danger">⚠ Exceeds estimated hours</small>`
    : "";

  // Add w-100 class if it's a single job
  const colClass = isSingleJob ? "col w-100" : "col";

  return `
        <div class="${colClass}">
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title text-truncate">
                        <a href="/job/${job.id}" class="text-decoration-none">
                            ${statusIcon} ${job.job_display_name}
                        </a>
                    </h5>
                    <p class="card-text mb-1"><strong>Status:</strong> ${statusDisplayName}</p>
                    <p class="card-text mb-1"><strong>Client:</strong> ${job.client_name || "N/A"}</p>
                    <p class="card-text mb-1"><strong>Estimated Hours:</strong> ${job.estimated_hours || 0}</p>
                    <p class="card-text mb-1">
                        <strong>Hours Spent:</strong> ${job.hours_spent || 0}
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

  const jobsContentHeight = jobsList.scrollHeight;

  if (jobsContentHeight > summarySection.offsetHeight) {
    jobsContainer.style.height = `${jobsContentHeight}px`;
  } else {
    jobsContainer.style.height = `${summarySection.offsetHeight}px`;
  }
}