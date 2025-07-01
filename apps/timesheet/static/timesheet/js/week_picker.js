export function initializeWeekPicker(modalId, apiUrlTemplate) {
  const modalContainer = document.querySelector(`#${modalId} .modal-body`);
  const modalTitle = document.querySelector(`#${modalId} .modal-title`);

  if (!modalContainer || !modalTitle) {
    console.error("Week Picker modal elements not found.");
    return;
  }

  function generateMonthsOfYear() {
    modalTitle.textContent = "Select a Month";
    modalContainer.innerHTML = "";

    const gridContainer = document.createElement("div");
    gridContainer.className = "row g-3";
    modalContainer.appendChild(gridContainer);

    const today = new Date();
    const currentYear = today.getFullYear();

    for (let month = 0; month < 12; month++) {
      const columnDiv = document.createElement("div");
      columnDiv.className = "col-md-4";

      const monthButton = document.createElement("button");
      const monthDate = new Date(currentYear, month, 1);
      monthButton.className = "btn btn-outline-secondary w-100";
      monthButton.textContent = monthDate.toLocaleDateString("en-NZ", {
        month: "long",
        year: "numeric",
      });

      monthButton.addEventListener("click", () => generateWeeksOfMonth(month));
      columnDiv.appendChild(monthButton);
      gridContainer.appendChild(columnDiv);
    }
  }

  function generateWeeksOfMonth(selectedMonth) {
    modalTitle.textContent = "Select a Week";
    modalContainer.innerHTML = "";

    const today = new Date();
    const year = today.getFullYear();
    const firstDayOfMonth = new Date(year, selectedMonth, 1);
    const lastDayOfMonth = new Date(year, selectedMonth + 1, 0);

    let currentDay = new Date(firstDayOfMonth);
    if (currentDay.getDay() !== 1) {
      currentDay.setDate(currentDay.getDate() - (currentDay.getDay() - 1));
    }

    while (currentDay <= lastDayOfMonth) {
      const weekStart = new Date(currentDay);
      const weekEnd = new Date(currentDay);
      weekEnd.setDate(weekStart.getDate() + 4);

      const weekButton = document.createElement("button");
      weekButton.className = "btn btn-outline-primary w-100 mb-2";
      weekButton.textContent = `${weekStart.toLocaleDateString("en-NZ", {
        day: "numeric",
        month: "long",
      })} - ${weekEnd.toLocaleDateString("en-NZ", {
        day: "numeric",
        month: "long",
      })}`;

      weekButton.addEventListener("click", () => {
        const formattedStartDate = weekStart.toISOString().split("T")[0];
        window.location.href = apiUrlTemplate.replace(
          "{start_date}",
          formattedStartDate,
        );
      });

      modalContainer.appendChild(weekButton);
      currentDay.setDate(currentDay.getDate() + 7);
    }

    const backButton = document.createElement("button");
    backButton.className = "btn btn-outline-secondary mt-3";
    backButton.textContent = "Back to Months";
    backButton.addEventListener("click", generateMonthsOfYear);

    modalContainer.appendChild(backButton);
  }

  generateMonthsOfYear();
}
