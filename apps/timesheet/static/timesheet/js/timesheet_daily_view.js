document.addEventListener("DOMContentLoaded", function () {
  const gridOptions = {
    columnDefs: [
      { headerName: "Staff Member", field: "staff_member", editable: true },
      { headerName: "Date", field: "date", editable: false },
      { headerName: "Job Name", field: "job_name", editable: true },
      {
        headerName: "Hours Worked",
        field: "hours_worked",
        editable: true,
        type: "numericColumn",
      },
      {
        headerName: "Billable",
        field: "billable",
        editable: true,
        cellRenderer: "agCheckboxRenderer",
      },
    ],
    defaultColDef: {
      flex: 1,
      minWidth: 100,
      filter: true,
      sortable: true,
      resizable: true,
    },
    rowData: [], // Placeholder, data will be populated via AJAX
    onGridReady: function (params) {
      loadDailyViewData(params.api);
    },
  };

  const eGridDiv = document.querySelector("#ag-grid-container");
  new agGrid.Grid(eGridDiv, gridOptions);

  function loadDailyViewData(gridApi) {
    const url = `/api/timesheets/daily/{{ date }}/`; // Endpoint to load data for the day
    fetch(url)
      .then((response) => response.json())
      .then((data) => {
        gridApi.setRowData(data);
        renderStaffChart(data);
        renderJobChart(data);
      })
      .catch((error) =>
        console.error("Error loading daily timesheet data:", error),
      );
  }
});
