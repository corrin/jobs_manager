export function calculateAmounts(data) {
  const hours = data.hours || 0;
  const minutes = hours * 60;

  const rateMultiplier =
    {
      Unpaid: 0.0,
      Ord: 1.0,
      1.5: 1.5,
      "2.0": 2.0,
    }[data.rate_type] || 1.0;

  const wageRate = window.timesheet_data.staff.wage_rate;
  data.wage_amount = hours * wageRate * rateMultiplier;

  const jobData = data.job_data;
  if (jobData) {
    data.bill_amount = hours * jobData.charge_out_rate;
  } else {
    data.bill_amount = 0;
  }

  data.items = 1;
  data.mins_per_item = minutes;
}

export function triggerAutoCalculationForAllRows() {
  const allNodes = [];
  window.grid.forEachNode((node) => allNodes.push(node));

  allNodes.forEach((node) => {
    const jobNumber = node.data.job_number;
    if (jobNumber) {
      const job = window.timesheet_data.jobs.find(
        (j) => j.job_number === jobNumber,
      );
      if (job) {
        node.setDataValue("job_name", job.name);
        node.setDataValue("client_name", job.client_name);
        node.setDataValue("job_data", job);
      }
      calculateAmounts(node.data); // Reuse existing function
    }
  });

  // Refresh affected grid cells
  window.grid.refreshCells({
    rowNodes: allNodes,
    columns: ["job_name", "client_name", "wage_amount", "bill_amount"],
  });
}

export function createNewRow() {
  return {
    id: null,
    job_number: null,
    timesheet_date: window.timesheet_data.timesheet_date,
    staff_id: window.timesheet_data.staff.id,
    is_billable: true,
    rate_type: "Ord",
    hours: 0,
    description: "",
  };
}

export function initializeGrid(gridDiv, gridOptions) {
  window.grid = agGrid.createGrid(gridDiv, gridOptions);
}

export function adjustGridHeight() {
  const gridElement = document.getElementById("timesheet-grid");
  if (!gridElement) {
    console.error("Grid container not found.");
    return;
  }

  let rowCount = 0;
  window.grid.forEachNode(() => rowCount++);
  const rowHeight = 40;
  const headerHeight = 50;
  const padding = 5;
  const maxHeight = Math.min(
    rowCount * rowHeight + headerHeight + padding,
    350,
  );

  gridElement.style.maxHeight = `${maxHeight}px`;
}