import { Environment } from "./env.js";
import { setupAdvancedSearch } from "./job/advanced_search.js";

import { renderMessages } from "/static/timesheet/js/timesheet_entry/messages.js"

console.log("kanban.js load started");

let currentSearchTerm = "";

document.addEventListener("DOMContentLoaded", function () {
  console.log("Script loaded and DOM fully loaded");

  initializeColumns();
  setupToggleArchived();
  setupAdvancedSearch();
  fetchAvailableStaff();

  document.getElementById("search").addEventListener("input", function () {
    filterJobs();
    updateColumnCounts();
  });
});

function initializeColumns() {
  const columns = document.querySelectorAll(".kanban-column");
  const columnIds = Array.from(columns).map((col) => col.id);

  columnIds.forEach((status) => {
    loadJobs(status);
  });

  initializeDragAndDrop();
}

function loadJobs(status) {
  const container = document.querySelector(`#${status} .job-list`);

  container.innerHTML = `
    <div class="loading-indicator">
      <i class="bi bi-hourglass-split"></i> Loading...
    </div>
  `;

  let url = `/kanban/fetch_jobs/${status}/`;
  if (currentSearchTerm) {
    url += `?search=${encodeURIComponent(currentSearchTerm)}`;
  }

  fetch(url)
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        renderJobs(status, data.jobs);
        applyStaffFilters();
        updateCounters(status, data.filtered_count, data.total);
        const loadMoreContainer = document.querySelector(
          `#${status}-load-more-container`,
        );
        if (loadMoreContainer) {
          loadMoreContainer.remove();
        }
      } else {
        console.error(`Error loading ${status} jobs:`, data.error);
        container.innerHTML = `
          <div class="error-message"> Error: ${data.error}</div>
        `;
      }
    })
    .catch((error) => {
      console.error(`Error loading ${status} jobs:`, error);
      container.innerHTML =
        '<div class="error-message"> Error loading jobs. Please try againg.</div>';
    });
}

function refreshAllColumns() {
  const columns = document.querySelectorAll(".kanban-column");
  const columnIds = Array.from(columns).map((col) => col.id);

  columnIds.forEach((status) => {
    loadJobs(status);
  });
}

function renderJobs(status, jobs) {
  const container = document.querySelector(`#${status} .job-list`);
  container.innerHTML = "";

  if (jobs.length === 0) {
    container.innerHTML = `
      <div class="empty-message">No jobs found</div>
    `;
    return;
  }

  jobs.forEach((job) => {
    console.log("Job:", job);
    const jobCard = createJobCard(job);
    container.appendChild(jobCard);
  });

  initializeStaffDragAndDrop();
}

function updateCounters(status, filteredCount, totalCount) {
  const countElement = document.getElementById(`${status}-count`);
  const totalElement = document.getElementById(`${status}-total`);

  if (countElement) countElement.textContent = filteredCount;
  if (totalElement) totalElement.textContent = totalCount;
}

function fetchStatusValues() {
  fetch("/api/fetch_status_values/")
    .then((response) => response.json())
    .then((statuses) => {
      Object.keys(statuses).forEach((status) => {
        loadJobs(status, true);
      });

      // After loading statuses, initialize drag and drop functionality
      initializeDragAndDrop();
    })
    .catch((error) => console.error("Error fetching status values:", error));
}

function createJobCard(job) {
  let card = document.createElement("div");
  card.className = "job-card";
  card.setAttribute("data-id", job.id);
  card.setAttribute("data-job-name", job.name || "");
  card.setAttribute("data-client-name", job.client_name ? job.client_name : "");
  card.setAttribute("data-job-description", job.description || "");
  card.setAttribute("data-job-number", job.job_number);

  card.setAttribute("data-assigned-staff", JSON.stringify(job.people || []));

  const clientName = job.client_name.length > 13 ? `${job.client_name.slice(0, 13)}...` : job.client_name

  card.innerHTML = `
    <a href="/job/${job.id}/">
      <div class="job-card-title">${job.job_number}</div>
      <div class="job-card-body small">
        ${job.client_name ? `<span class="fw-semibold">${clientName}</span><br>` : ""}
        ${job.name}
      </div>
    </a>
    <div class="job-assigned-staff">
    </div>
  `;

  const staffContainer = card.querySelector(".job-assigned-staff");
  if (job.people && job.people.length > 0) {
    job.people.forEach(staff => {
      const staffIcon = document.createElement("div");
      staffIcon.className = "staff-avatar staff-avatar-sm";
      staffIcon.setAttribute("data-staff-id", staff.id);
      staffIcon.innerHTML = generateAvatar(staff);
      staffIcon.title = staff.display_name;
      staffContainer.appendChild(staffIcon);
    });
  }

  // Tooltip container (Hidden initially)
  let tooltip = document.createElement("div");
  tooltip.className = "job-tooltip";
  tooltip.textContent = job.description;
  tooltip.style.display = "none";

  // Append tooltip to document body (so it floats near cursor)
  document.body.appendChild(tooltip);

  // Show tooltip on hover
  card.addEventListener("mouseenter", (event) => {
    if (job.description) {
      tooltip.style.display = "block";
      tooltip.style.left = `${event.pageX + 10}px`;
      tooltip.style.top = `${event.pageY + 10}px`;
    }
  });

  // Move tooltip with cursor
  card.addEventListener("mousemove", (event) => {
    tooltip.style.left = `${event.pageX + 10}px`;
    tooltip.style.top = `${event.pageY + 10}px`;
  });

  // Hide tooltip on mouse leave
  card.addEventListener("mouseleave", () => {
    tooltip.style.display = "none";
  });

  return card;
}

// Initialize SortableJS to allow moving jobs between columns
function initializeDragAndDrop() {
  document.querySelectorAll(".job-list").forEach((container) => {
    new Sortable(container, {
      group: "shared",
      animation: 150,
      ghostClass: "sortable-ghost",
      chosenClass: "sortable-drag",
      dragClass: "sortable-drag",
      onStart: function () {
        document.querySelectorAll(".kanban-column").forEach((col) => {
          col.classList.add("drop-target-potential");
        });
      },
      onEnd: function (evt) {
        const itemEl = evt.item;
        const oldStatus = evt.from.closest(".kanban-column").id;
        const newStatus = evt.to.closest(".kanban-column").id;
        const jobId = itemEl.getAttribute("data-id");

        // Remove potential destiny class
        document.querySelectorAll(".kanban-column").forEach((col) => {
          col.classList.remove("drop-target-potential");
        });

        if (!oldStatus || !newStatus || oldStatus === newStatus) {
          return;
        }

        console.log(`Job ${jobId} moved from ${oldStatus} to ${newStatus}`);

        updateJobStatus(jobId, newStatus);

        // Update affected column counters
        updateColumnHeader(oldStatus);
        updateColumnHeader(newStatus);

        updateColumnCounts();
      },
    });
  });
}

function updateColumnHeader(status) {
  const column = document.getElementById(status);
  if (!column) {
    console.error(`Column not found for status: ${status}`);
    return;
  }

  const jobCards = column.querySelectorAll(".job-card");
  const countDisplay = document.querySelector(`#${status}-count`);

  if (countDisplay) {
    countDisplay.textContent = jobCards.length;
  }
}

function updateColumnCounts() {
  // Update count for each column
  document.querySelectorAll(".kanban-column").forEach((column) => {
    const columnId = column.id;
    const jobList = column.querySelector(".job-list");
    const countDisplay = document.querySelector(`#${columnId}-count`);

    if (countDisplay && jobList) {
      const visibleCount = Array.from(jobList.children).filter(
        (child) => child.style.display !== "none",
      ).length;
      countDisplay.textContent = visibleCount;
    }
  });
}

function filterJobs() {
  const searchTerm = document.getElementById("search").value.toLowerCase();

  document.querySelectorAll(".kanban-column").forEach((column) => {
    const jobCards = column.querySelectorAll(".job-card");
    jobCards.forEach((card) => {
      const combinedText = [
        card.dataset.jobName,
        card.dataset.jobDescription,
        card.dataset.clientName,
        card.dataset.jobNumber,
      ]
        .join(" ")
        .toLowerCase();
      card.style.display = combinedText.includes(searchTerm) ? "" : "none";
    });
  });
}

function updateJobStatus(jobId, newStatus) {
  fetch(`/jobs/${jobId}/update_status/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({
      status: newStatus,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Atualizar contadores
        refreshAllColumns();
      } else {
        alert("Failed to update job status: " + data.error);
        // Recarregar para restaurar o estado
        refreshAllColumns();
      }
    })
    .catch((error) => {
      console.error("Error updating job status:", error);
      alert("Failed to update job status. Please try again.");
      refreshAllColumns();
    });
}

function getCookie(name) {
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

function setupToggleArchived() {
  const toggleButton = document.getElementById("toggleArchive");
  const archiveContainer = document.getElementById("archiveContainer");

  let archivedVisible = false;

  loadJobs("archived");

  toggleButton.addEventListener("click", () => {
    archivedVisible = !archivedVisible;

    switch (archivedVisible) {
      case true:
        archiveContainer.style.display = "grid";
        this.querySelector("i").className = "bi bi-chevron-up";
        loadJobs("archived");
        break;
      default:
        archiveContainer.style.display = "none";
        this.querySelector("i").className = "bi bi-chevron-down";
        break;
    }
  });
}

function fetchAvailableStaff() {
  fetch("/accounts/api/staff/all", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Actual-Users": "True",
    },
  })
    .then((response) => {
      if (Environment.isDebugMode())
        console.log("Staff API response status:", response.status);
      return response.json().then((data) => ({ data, ok: response.ok }));
    })
    .then(({ data, ok }) => {
      if (!ok) {
        throw new Error("Error while trying to fetch available staff users: ", e);
      }

      renderStaffPanel(data);
      setupStaffFiltering();
    })
    .catch(error => {
      console.error(error);
    });
}

function renderStaffPanel(staff) {
  const staffPanelContainer = document.getElementById("staff-panel");
  if (!staffPanelContainer) return;

  staffPanelContainer.innerHTML = '<h6>Team Members</h6><div class="staff-list"></div>';
  const staffList = staffPanelContainer.querySelector(".staff-list");

  staff.forEach(s => {
    const staffIcon = document.createElement("div");
    staffIcon.className = "staff-avatar draggable-staff";
    staffIcon.setAttribute("data-staff-id", s.id);
    staffIcon.innerHTML = generateAvatar(s);

    staffIcon.title = s.display_name;
    staffList.appendChild(staffIcon);
  });

  initializeStaffDragAndDrop();
}

function generateAvatar(staff) {
  const predefinedColors = [
    "#3498db", // blue
    "#2ecc71", // green
    "#e74c3c", // red
    "#9b59b6", // purple
    "#f39c12", // orange
    "#1abc9c", // teal
    "#d35400", // dark orange
    "#c0392b", // dark red
    "#8e44ad", // dark purple
    "#16a085", // dark teal
    "#27ae60", // dark green
    "#2980b9", // dark blue
    "#f1c40f", // yellow
    "#e67e22", // orange
    "#34495e"  // navy blue
  ];

  if (!staff.icon) {
    const initials = staff.display_name
      .split(' ')
      .map(part => part.charAt(0))
      .join('')
      .toUpperCase()
      .substring(0, 2);

    const colorIndex = Math.abs(staff.display_name.split('').reduce((acc, char) =>
      acc + char.charCodeAt(0), 0)) % predefinedColors.length;

    const color = predefinedColors[colorIndex];

    return `<div class="staff-initials" style="background-color: ${color}">${initials}</div>`;
  }
  return `<img src="${staff.icon}" alt="${staff.display_name}" class="staff-img">`;
}

function initializeStaffDragAndDrop() {
  const staffItems = document.querySelectorAll(".draggable-staff");
  staffItems.forEach(item => {
    new Sortable(item.parentElement, {
      group: {
        name: "staff",
        pull: "clone",
        put: true
      },
      sort: false,
      animation: 150,
      ghostClass: "staff-ghost",
      chosenClass: "staff-chosen",
      dragClass: "staff-drag",
      onStart: function () {
        const card = evt.item.closest(".job-card");
        if (card) evt.item.dataset.originJobId = card.dataset.id;
      },
      onAdd: function (evt) {
        const originCard = evt.from.closest(".job-card");
        let jobId;

        if (originCard) {
          jobId = originCard.dataset.id;
        } else if (evt.item.dataset.originJobId) {
          jobId = evt.item.dataset.originJobId;
        } else {
          console.card.error("No job ID found for the dragged staff item.");
          return;
        }

        const staffId = evt.item.dataset.staffId;
        evt.item.remove();
        removeStaffFromJob(jobId, staffId);
      },
      onEnd: function () { }
    });
  });

  const jobLists = document.querySelectorAll(".job-list");
  jobLists.forEach(list => {
    list.querySelectorAll(".job-card").forEach(card => {
      const staffContainer = card.querySelector(".job-assigned-staff");

      if (!staffContainer) return;

      new Sortable(staffContainer, {
        group: {
          name: "staff",
          pull: true,
          put: true
        },
        animation: 150,
        onAdd: function (evt) {
          const staffId = evt.item.getAttribute("data-staff-id");
          const jobId = evt.to.closest(".job-card").getAttribute("data-id");

          evt.item.remove();
          assignStaffToJob(jobId, staffId);
        }
      });
    })
  });
}

function assignStaffToJob(jobId, staffId) {
  fetch(`/api/job/${jobId}/assignment`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      staff_id: staffId,
      job_id: jobId
    })
  })
    .then(response => response.json())
    .then(data => {
      if (!data.success) throw new Error(data.error);
      const columns = document.querySelectorAll(".kanban-column");
      const columnIds = Array.from(columns).map((col) => col.id);

      columnIds.forEach((status) => {
        loadJobs(status);
      });
    })
    .catch(error => {
      console.error("Error assigning staff:", error);
      renderMessages([{ level: "danger", message: `Error assigning staff to job ${jobId}` + error }]);
    });
}

function removeStaffFromJob(jobId, staffId) {
  fetch(`/api/job/${jobId}/assignment`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({ job_id: jobId, staff_id: staffId })
  })
    .then(r => r.json())
    .then(data => data.success ? refreshAllColumns()
      : renderMessages([{ level: "danger", message: data.error }]))
    .catch(err => console.error(err));
}

let activeStaffFilters = [];
function setupStaffFiltering() {
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".draggable-staff")) return;
    const staffIcon = e.target.closest(".draggable-staff");
    const staffId = staffIcon.getAttribute("data-staff-id");

    toggleStaffFilter(staffId, staffIcon);

    applyStaffFilters();
  });
}

function toggleStaffFilter(staffId, staffIcon) {
  const index = activeStaffFilters.indexOf(staffId);

  if (index !== -1) {
    activeStaffFilters.splice(index, 1);
    staffIcon.classList.remove("staff-filter-active");
  } else {
    activeStaffFilters.push(staffId);
    staffIcon.classList.add("staff-filter-active");
  }
}

function applyStaffFilters() {
  if (activeStaffFilters.length === 0) {
    document.querySelectorAll(".job-card").forEach(card => {
      card.style.display = "";
    });
    return;
  }

  document.querySelectorAll(".job-card").forEach(card => {
    const assignedStaffJson = card.getAttribute("data-assigned-staff");
    let assignedStaff = [];

    try {
      assignedStaff = JSON.parse(assignedStaffJson || '[]');
    } catch (e) {
      console.error("Error parsing assigned staff:", e);
    }

    const hasMatchingStaff = assignedStaff.some(staff => 
      activeStaffFilters.includes(staff.id.toString())
    );

    card.style.display = hasMatchingStaff ? "" : "none";
  });

  updateColumnCounts();
}
