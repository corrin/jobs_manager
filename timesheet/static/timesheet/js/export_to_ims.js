function checkIMSButton(IMSButton) {
  if (IMSButton && "checked" in IMSButton) {
    IMSButton.checked = true;
    if (window.DEBUG_MODE) {
      console.log("IMS button checked successfully");
    }
  } else {
    console.warn("Invalid element!");
    if (window.DEBUG_MODE) {
      console.log("Failed to check IMS button: invalid element");
    }
    return false;
  }
}

function formatDate(dateStr) {
  try {
    // Remove ordinal suffixes and clean up the string
    dateStr = dateStr.replace(/(st|nd|rd|th)/, "").trim();

    const date = new Date(dateStr);

    // Check if date is valid
    if (isNaN(date.getTime())) {
      throw new Error("Invalid date");
    }

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  } catch (error) {
    console.error("Error formatting date:", error);
    return null;
  }
}

export function checkQueryParam(exportToIMSButton) {
  const params = new URLSearchParams(window.location.search);
  const exportToIMSQuery = params.get("export_to_ims") === "1";

  if (exportToIMSQuery) {
    exportToIMSButton.click();
    checkIMSButton(exportToIMSButton);
    toggleTableToIMS();
    if (window.DEBUG_MODE) {
      console.log(
        "Export to IMS query parameter detected, toggling table to IMS view",
      );
    }
  }
}

export async function toggleTableToIMS() {
  const IMSButton = document.getElementById("exportToIMS");
  const dateSpan = document.getElementById("current-week-display");
  const dateText = dateSpan.textContent.trim();
  const firstDate = dateText.split("-")[0].trim();

  if (IMSButton && !IMSButton.checked) {
    const url = new URL(window.location.href);
    url.searchParams.delete("export_to_ims");

    window.history.replaceState({}, "", url);
    window.location.reload();
    return;
  }

  console.log(
    "First date before format: ",
    firstDate,
    "| After:",
    formatDate(firstDate),
  );

  await fetch("/timesheets/export_to_ims/", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
      action: "export_to_ims",
      "X-Date": formatDate(firstDate),
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        updateOverviewTable(data);
        updateNavigationUrls(data);
        updateTableHeaderIMS(data.week_days);
        updateBillableHeader();
      }
      if (window.DEBUG_MODE) {
        console.log("Export to IMS successful:", data);
      }
    })
    .catch((error) => {
      console.error("Error during export to IMS:", error);
    });
}

function updateOverviewTable(data) {
  const table = document.getElementById("overviewTable");
  if (!table) {
    console.error("Overview Table not found.");
    return;
  }
  const tbody = table.querySelector("tbody");
  if (!tbody) {
    console.error("Table body not found.");
    return;
  }

  table.classList.add("ims-view-container");
  tbody.innerHTML = "";

  data.staff_data.forEach((staff) => {
    const tr = document.createElement("tr");

    // Staff name cell
    const tdName = document.createElement("td");
    tdName.textContent = staff.name;
    tr.appendChild(tdName);

    // For each week day, create a formatted cell
    staff.weekly_hours.forEach((dayData) => {
      const td = document.createElement("td");
      td.classList.add("ims-data-cell");

      const isLeave = dayData.status === "Leave";
      const leaveType = isLeave ? detectLeaveType(dayData.leave_type) : null;

      const leaveHours = isLeave ? dayData.leave_hours || 0 : 0;
      const workHours = isLeave
        ? (dayData.hours || 0) - leaveHours
        : dayData.hours || 0;

      let cellContent = `
                <div class="ims-hour-total">
                    <span>Total</span>
                    <span>${formatHourValue(workHours)}</span>
                </div>`;

      let annualLeaveHours = 0;
      let sickLeaveHours = 0;
      let otherLeaveHours = 0;

      if (isLeave && leaveType) {
        switch (leaveType.toLowerCase()) {
          case "annual":
            annualLeaveHours += dayData.hours;
            break;
          case "sick":
            sickLeaveHours += dayData.hours;
            break;
          default:
            otherLeaveHours += dayData.hours;
            break;
        }
      }

      const isWarning = dayData.status === "⚠";
      const isComplete = dayData.status === "✓";
      const isEmpty = dayData.hours === 0;

      if (
        dayData.standard_hours > 0 ||
        dayData.time_and_half_hours > 0 ||
        dayData.double_time_hours > 0
      ) {
        cellContent += `
                    <div class="ims-work-section">
                        <div class="ims-leave-header">Work Hours</div>
                        ${
                          dayData.standard_hours > 0
                            ? `<div class="ims-hour-row">
                                <span>Standard</span>
                                <span>${formatHourValue(dayData.standard_hours)}</span>
                            </div>`
                            : ""
                        }
                        
                        ${
                          dayData.time_and_half_hours > 0
                            ? `<div class="ims-hour-row">
                                <span class="ims-hour-label">1.5x</span>
                                <span class="ims-hour-value">${formatHourValue(dayData.time_and_half_hours)}</span>
                            </div>`
                            : ""
                        }
                        
                        ${
                          dayData.double_time_hours > 0
                            ? `<div class="ims-hour-row">
                                <span class="ims-hour-label">2x</span>
                                <span class="ims-hour-value">${formatHourValue(dayData.double_time_hours)}</span>
                            </div>`
                            : ""
                        }
                    </div>
                `;
      }

      if (isLeave && dayData.leave_hours > 0) {
        const leaveTypeLabel = getLeaveTypeLabel(leaveType);
        const leaveClass = `ims-leave-${leaveType.toLowerCase()}`;

        cellContent += `
                    <div class="ims-leave-section ${leaveClass}">
                        <div class="ims-leave-header">${leaveTypeLabel} Leave</div>
                        <div class="ims-hour-row">
                            <span>Hours</span>
                            <span>${formatHourValue(dayData.leave_hours)}</span>
                        </div>
                    </div>
                `;
      }

      if (isEmpty) {
        cellContent += `<div class="ims-status ims-status-empty">-</div>`;
      }

      if (isWarning) {
        cellContent += `<div class="ims-status ims-status-warning">⚠</div>`;
      }

      if (dayData.overtime > 0) {
        cellContent += `<div class="ims-status ims-status-overtime">OT: ${formatHourValue(dayData.overtime)}</div>`;
      }

      if (isComplete) {
        cellContent += `<div class="ims-status ims-status-ok">✓</div>`;
      }

      td.innerHTML = cellContent;
      tr.appendChild(td);
    });

    const tdTotal = document.createElement("td");
    tdTotal.classList.add("ims-data-cell");

    const stdHours = parseFloat(staff.total_standard_hours || 0);
    const timeHalfHours = parseFloat(staff.total_time_and_half_hours || 0);
    const doubleTimeHours = parseFloat(staff.total_double_time_hours || 0);

    const totalWorkHours = stdHours + timeHalfHours + doubleTimeHours;

    const totalLeaveHours =
      parseFloat(staff.total_annual_leave_hours || 0) +
      parseFloat(staff.total_sick_leave_hours || 0) +
      parseFloat(staff.total_other_leave_hours || 0);

    tdTotal.innerHTML = `
            <div class="ims-hour-total">
                <span>Total</span>
                <span>${formatHourValue(staff.total_hours)}</span>
            </div>

            ${
              totalWorkHours > 0
                ? `<div class="ims-work-section">
                    <div class="ims-section-header">Work Hours</div>
                    ${
                      staff.total_standard_hours > 0
                        ? `<div class="ims-hour-row">
                            <span>Standard</span>
                            <span>${formatHourValue(staff.total_standard_hours)}</span>
                        </div>`
                        : ""
                    }
                    ${
                      staff.total_time_and_half_hours > 0
                        ? `<div class="ims-hour-row">
                            <span>1.5x</span>
                            <span>${formatHourValue(staff.total_time_and_half_hours)}</span>
                        </div>`
                        : ""
                    }
                    ${
                      staff.total_double_time_hours > 0
                        ? `<div class="ims-hour-row">
                            <span>2x</span>
                            <span>${formatHourValue(staff.total_double_time_hours)}</span>
                        </div>`
                        : ""
                    }
                </div>`
                : ""
            }

            ${
              totalLeaveHours > 0
                ? `<div class="ims-leave-section">
                    <div class="ims-section-header">Leave Hours</div>
                    ${
                      staff.total_annual_leave_hours > 0
                        ? `<div class="ims-hour-row ims-leave-annual">
                            <span>Annual</span>
                            <span>${formatHourValue(staff.total_annual_leave_hours)}</span>
                        </div>`
                        : ""
                    }
                    ${
                      staff.total_sick_leave_hours > 0
                        ? `<div class="ims-hour-row ims-leave-sick">
                            <span>Sick</span>
                            <span>${formatHourValue(staff.total_sick_leave_hours)}</span>
                        </div>`
                        : ""
                    }
                    ${
                      staff.total_other_leave_hours > 0
                        ? `<div class="ims-hour-row ims-leave-other">
                            <span>Other</span>
                            <span>${formatHourValue(staff.total_other_leave_hours)}</span>
                        </div>`
                        : ""
                    }
                </div>`
                : ""
            }

            ${
              staff.total_overtime > 0
                ? `<div class="ims-hour-row">
                    <span class="ims-hour-label">Overtime</span>
                    <span class="ims-hour-value">${formatHourValue(staff.total_overtime)}</span>
                </div>`
                : ""
            }
        `;

    tr.appendChild(tdTotal);

    const tdBillable = document.createElement("td");
    tdBillable.innerHTML = `
            <div class="ims-hour-total">
                <span>Billable</span>
                <span>${formatHourValue(staff.total_billable_hours)}</span>
            </div>
            <div class="ims-hour-row">
                <span class="ims-hour-label">Percentage</span>
                <span class="ims-hour-value">${staff.billable_percentage}%</span>
            </div>
        `;
    tdBillable.classList.add("ims-data-cell");
    tr.appendChild(tdBillable);

    tbody.appendChild(tr);
  });
}

/**
 * Determines the leave type based on the job name
 * @param {string} leaveJobName Leave job name
 * @returns {string} Leave type (Annual, Sick, Other)
 */
function detectLeaveType(leaveJobName) {
  if (!leaveJobName) return "Other";

  const lowerName = leaveJobName.toLowerCase();

  if (lowerName.includes("annual")) {
    return "Annual";
  }

  if (lowerName.includes("sick")) {
    return "Sick";
  }

  return "Other";
}

/**
 * Returns the proper icon for the leave type
 * @param {string} leaveType
 */
function getLeaveIcon(leaveType) {
  switch (leaveType) {
    case "Annual":
      return "far fa-calendar-alt";
    case "Sick":
      return "fas fa-head-side-cough";
    default:
      return "fas fa-bed";
  }
}

/**
 * Returns the proper label for the leave type
 * @param {string} leaveType
 */
function getLeaveTypeLabel(leaveType) {
  switch (leaveType) {
    case "Annual":
      return "Annual";
    case "Sick":
      return "Sick";
    default:
      return "Other";
  }
}

function formatHourValue(hours) {
  if (hours === null || hours === undefined || isNaN(hours)) return "0.0";
  return parseFloat(hours).toFixed(1);
}

function updateTableHeaderIMS(weekDays) {
  const headerRow = document.querySelector("#overviewTable thead tr");

  if (!headerRow) {
    console.error("Table header not found.");
    return;
  }

  headerRow.querySelectorAll("th").forEach((th) => {
    th.classList.add("ims-header-cell");
  });

  const headerCells = headerRow.querySelectorAll("th");

  weekDays.forEach((dayStr, index) => {
    try {
      const day = parseDateWithoutTimezone(dayStr);

      if (isNaN(day.getTime())) {
        throw new Error("Invalid date:", dayStr);
      }

      const dayLabel = day.toLocaleDateString("en-AU", {
        weekday: "short",
        day: "numeric",
        month: "numeric",
      });

      if (headerCells[index + 1]) {
        headerCells[index + 1].textContent = dayLabel;
      }
    } catch (error) {
      console.error(`Error updating data ${dayStr}:`, error);
      if (headerCells[index + 1]) {
        headerCells[index + 1].textContent = "Day " + (index + 1);
      }
    }
  });
}

function updateNavigationUrls(data) {
  const queryParam = `export_to_ims=${1}`;
  const prevLink = document.getElementById("prevWeekLink");
  const nextLink = document.getElementById("nextWeekLink");

  if (prevLink && data.prev_week_url) {
    prevLink.href = data.prev_week_url.includes("?")
      ? `${data.prev_week_url}&${queryParam}`
      : `${data.prev_week_url}?${queryParam}`;
  }
  if (nextLink && data.next_week_url) {
    nextLink.href = data.next_week_url.includes("?")
      ? `${data.next_week_url}&${queryParam}`
      : `${data.next_week_url}?${queryParam}`;
  }
}

function updateBillableHeader() {
  const headerRow = document.querySelector("#overviewTable thead tr");
  if (!headerRow) {
    console.error("Table header not found.");
    return;
  }
  const headerCells = headerRow.querySelectorAll("th");
  if (headerCells.length < 2) {
    console.error("Not enough header cells.");
    return;
  }
  headerCells[headerCells.length - 2].textContent = "Weekly Total";
  headerCells[headerCells.length - 1].textContent = "Billable Hours";
}

function parseDateWithoutTimezone(dateStr) {
  const parts = dateStr.split("-");
  return new Date(parts[0], parts[1] - 1, parts[2], 12);
}