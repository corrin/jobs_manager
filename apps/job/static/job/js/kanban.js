import { Environment } from "/static/js/env.js";
import { setupAdvancedSearch } from "./advanced_search.js";

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

  // Don't call initializeDragAndDrop() here - it runs before async loadJobs() completes
  // Each column initializes its own drag and drop in renderJobs() after jobs are loaded
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

  // Disable Sortable during job loading to prevent reorder events
  if (container && container.sortableJobsInstance) {
    container.sortableJobsInstance.destroy();
    container.sortableJobsInstance = null;
  }

  container.innerHTML = "";

  if (jobs.length === 0) {
    container.innerHTML = `
      <div class="empty-message">No jobs found</div>
    `;
    // Still need to initialize drag and drop for empty columns so they can receive drops
    initializeDragAndDropForColumn(container);
    initializeStaffDragAndDrop();
    return;
  }

  jobs.forEach((job) => {
    console.log("Job:", job);
    const jobCard = createJobCard(job);
    container.appendChild(jobCard);
  });

  // Initialize drag and drop for this specific column after jobs are loaded
  // Can't rely on global initializeDragAndDrop() because it runs before async loadJobs() completes
  initializeDragAndDropForColumn(container);
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
  card.setAttribute("data-created-by-id", job.created_by_id || "");

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

// Initialize SortableJS for a specific container
function initializeDragAndDropForColumn(container) {
  // Destroy existing instance if any, to prevent duplicates
  if (container.sortableJobsInstance) {
    container.sortableJobsInstance.destroy();
  }
  container.sortableJobsInstance = new Sortable(container, {
    group: "jobGroup",
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
      const oldCol = evt.from.closest(".kanban-column");
      const newCol = evt.to.closest(".kanban-column");
      const oldStatus = oldCol.id;
      const newStatus = newCol.id;
      const jobId = itemEl.dataset.id;

      document
        .querySelectorAll(".kanban-column")
        .forEach((c) => c.classList.remove("drop-target-potential"));

      // collect cards in the dest column
      let cards = Array.from(newCol.querySelectorAll(".job-card"));
      if (cards.length === 0) cards = [itemEl];      // column was empty

      const total = cards.length;
      let index = evt.newIndex;
      if (index >= total) index = total - 1; // clamp
      if (index < 0) index = 0;

      let beforeId = null;
      let afterId = null;

      switch (true) {
        // top
        case index === 0:
          afterId = cards[1] ? cards[1].dataset.id : null;
          break;

        // bottom
        case index === total - 1:
          beforeId = cards[total - 2] ? cards[total - 2].dataset.id : null;
          break;

        // middle
        default:
          beforeId = cards[index - 1].dataset.id;
          afterId = cards[index + 1].dataset.id;
          break;
      }

      const payload = {
        before_id: beforeId,
        after_id: afterId,
        status: newStatus
      };

      fetch(`/job/${jobId}/reorder/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
        },
        body: JSON.stringify(payload),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            console.log("Job reordered successfully");
          } else {
            console.error("Error reordering job:", data.error);
          }
        })
        .catch((error) => {
          console.error("Network error:", error);
        });

      // Update status if moved between columns
      if (oldStatus !== newStatus) {
        updateJobStatus(jobId, newStatus);
      }
    },
  });
}

// Initialize SortableJS to allow moving jobs between columns
function initializeDragAndDrop() {
  document.querySelectorAll(".job-list").forEach((container) => {
    // Destroy existing instance if any, to prevent duplicates
    if (container.sortableJobsInstance) {
      container.sortableJobsInstance.destroy();
    }
    container.sortableJobsInstance = new Sortable(container, {
      group: "jobGroup",
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
        const oldCol = evt.from.closest(".kanban-column");
        const newCol = evt.to.closest(".kanban-column");
        const oldStatus = oldCol.id;
        const newStatus = newCol.id;
        const jobId = itemEl.dataset.id;

        document
          .querySelectorAll(".kanban-column")
          .forEach((c) => c.classList.remove("drop-target-potential"));

        // collect cards in the dest column
        let cards = Array.from(newCol.querySelectorAll(".job-card"));
        if (cards.length === 0) cards = [itemEl];      // column was empty

        const total = cards.length;
        let index = evt.newIndex;
        if (index >= total) index = total - 1; // clamp
        if (index < 0) index = 0;

        let beforeId = null;
        let afterId = null;

        switch (true) {
          // top
          case index === 0:
            afterId = cards[1] ? cards[1].dataset.id : null;
            break;

          // bottom
          case index === total - 1:
            beforeId = cards[total - 2] ? cards[total - 2].dataset.id : null;
            break;

          // middle
          default:
            beforeId = cards[index - 1].dataset.id;
            afterId = cards[index + 1].dataset.id;
            break;
        }

        const payload = {
          before_id: beforeId,
          after_id: afterId,
          status: newStatus
        };

        fetch(`/job/${jobId}/reorder/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
          },
          body: JSON.stringify(payload)
        })
          .then((res) => res.json())
          .then((data) => {
            if (!data.success) {
              console.error("reorder failed:", data.error);
              refreshAllColumns();
              alert("Could not reorder job: " + (data.error || "Unknown error"));
              return;
            }
            itemEl.dataset.priority = data.priority;
            loadJobs(oldStatus);
            if (newStatus !== oldStatus) loadJobs(newStatus);
          })
          .catch((err) => {
            console.error("network error:", err);
            refreshAllColumns();
            alert("Network error. Please reload.");
          });
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
  let archivedLoaded = false;

  // Don't load archived jobs on init - causes Sortable errors on hidden container

  toggleButton.addEventListener("click", () => {
    archivedVisible = !archivedVisible;
    const icon = toggleButton.querySelector("i");

    switch (archivedVisible) {
      case true:
        archiveContainer.style.display = "grid";
        if (icon) icon.className = "bi bi-chevron-up";
        // Only load archived jobs once, when first opened
        if (!archivedLoaded) {
          loadJobs("archived");
          archivedLoaded = true;
        }
        break;
      default:
        archiveContainer.style.display = "none";
        if (icon) icon.className = "bi bi-chevron-down";
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
        const errorMessage = data && data.detail ? data.detail : "Unknown error fetching staff.";
        throw new Error(`Error while trying to fetch available staff users: ${errorMessage}`);
      }

      renderStaffPanel(data);
      setupStaffFiltering();
    })
    .catch(error => {
      console.error(error);
      renderMessages([{ level: "danger", message: "Could not load team members." }]);
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
  const staffPanelList = document.querySelector("#staff-panel .staff-list");
  if (staffPanelList) {
    if (staffPanelList.sortableStaffPoolInstance) {
      staffPanelList.sortableStaffPoolInstance.destroy();
    }
    staffPanelList.sortableStaffPoolInstance = new Sortable(staffPanelList, {
      group: {
        name: "staffPool",
        pull: "clone",
        put: ["staffOnJob"]
      },
      sort: false,
      animation: 150,
      onAdd: function (evt) {
        const staffId = evt.item.dataset.staffId;
        const fromJobCardElement = evt.from.closest(".job-card");

        if (fromJobCardElement) {
          const jobId = fromJobCardElement.dataset.id;
          console.log(`Staff ${staffId} returned to pool from job ${jobId}.`);
          removeStaffFromJob(jobId, staffId);
        }
        evt.item.remove();
      }
    });
  }


  document.querySelectorAll(".job-card").forEach(card => {
    const staffContainerOnJob = card.querySelector(".job-assigned-staff");
    if (staffContainerOnJob) {
      if (staffContainerOnJob.sortableOnJobInstance) {
        staffContainerOnJob.sortableOnJobInstance.destroy();
      }
      staffContainerOnJob.sortableOnJobInstance = new Sortable(staffContainerOnJob, {
        group: {
          name: "staffOnJob",
          pull: true,
          put: ["staffPool", "staffOnJob"]
        },
        animation: 150,
        onAdd: function (evt) {
          const staffId = evt.item.getAttribute("data-staff-id");
          const jobId = evt.to.closest(".job-card").getAttribute("data-id");

          const fromStaffPool = evt.from.isEqualNode(staffPanelList);

          console.log(`Staff ${staffId} added/moved to job ${jobId}. From pool: ${fromStaffPool}`);
          assignStaffToJob(jobId, staffId);
        }
      });
    }
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
      if (!data.success) throw new Error(data.error || "Failed to assign staff.");
      const columns = document.querySelectorAll(".kanban-column");
      const columnIds = Array.from(columns).map((col) => col.id);

      columnIds.forEach((status) => {
        loadJobs(status);
      });
    })
    .catch(error => {
      console.error("Error assigning staff:", error);
      renderMessages([{ level: "danger", message: `Error assigning staff: ${error.message || error}` }]);
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
    .then(data => {
      if (data.success) {
        refreshAllColumns();
      } else {
        renderMessages([{ level: "danger", message: data.error || "Failed to remove staff." }]);
      }
    })
    .catch(err => {
      console.error("Error removing staff:", err);
      renderMessages([{ level: "danger", message: `Error removing staff: ${err.message || err}` }]);
    });
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
    // Ensure the main search filter is reapplied if it exists
    filterJobs();
    updateColumnCounts();
    return;
  }

  document.querySelectorAll(".job-card").forEach(card => {
    const assignedStaffJson = card.getAttribute("data-assigned-staff");
    const createdById = card.getAttribute("data-created-by-id");
    let assignedStaffIds = [];

    try {
      // Parse assigned staff which is an array of objects, map to their IDs
      const staffObjects = JSON.parse(assignedStaffJson || '[]');
      assignedStaffIds = staffObjects.map(staff => staff.id.toString());
    } catch (e) {
      console.error("Error parsing assigned staff:", e);
    }

    // A job is visible if any of the active staff filters match an assigned staff member
    // OR if any of the active staff filters match the creator of the job.
    const isAssignedToActiveStaff = assignedStaffIds.some(staffId =>
      activeStaffFilters.includes(staffId)
    );

    const isCreatedByActiveStaff = createdById ? activeStaffFilters.includes(createdById.toString()) : false;

    // Card should be visible if it matches the general search term (if any)
    // AND (it's assigned to an active staff filter OR created by an active staff filter)
    const searchTerm = document.getElementById("search").value.toLowerCase();
    const combinedText = [
      card.dataset.jobName,
      card.dataset.jobDescription,
      card.dataset.clientName,
      card.dataset.jobNumber,
    ]
      .join(" ")
      .toLowerCase();

    const matchesGeneralSearch = searchTerm ? combinedText.includes(searchTerm) : true;

    if (matchesGeneralSearch && (isAssignedToActiveStaff || isCreatedByActiveStaff)) {
      card.style.display = "";
    } else {
      card.style.display = "none";
    }
  });

  updateColumnCounts();
}
