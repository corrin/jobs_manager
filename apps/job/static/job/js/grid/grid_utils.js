import { createNewRow } from "../deserialize_job_pricing.js";
import { lockQuoteGrids } from "../job_buttons/button_utils.js";
import { sections } from "./grid_initialization.js";
import { Environment } from "/static/js/env.js";

export function calculateGridHeight(gridApi, numRows) {
  const rowHeight = gridApi.getSizesForCurrentTheme().rowHeight || 28;
  const headerElement = document.querySelector(".ag-header");
  const headerHeight = headerElement ? headerElement.offsetHeight : 32;

  return numRows * rowHeight + headerHeight;
}

// Helper function to check rows and add correct overflows
export function updateGridOverflowClasses() {
  Object.keys(window.grids).forEach((gridKey) => {
    const api = window.grids[gridKey]?.api;
    if (api) {
      const gridElement = document.querySelector(`#${gridKey}`);
      if (gridElement) {
        const rowCount = api.getDisplayedRowCount();
        if (rowCount < 13) {
          gridElement.classList.add("ag-rows-few");
          gridElement.classList.remove("ag-rows-many");
        } else {
          gridElement.classList.add("ag-rows-many");
          gridElement.classList.remove("ag-rows-few");
        }
      }
    }
  });
}

// Helper function to determine the current UI mode (simple/complex)
function isComplex() {
  const complexJobElement = document.getElementById("complex-job");
  if (complexJobElement) {
    return complexJobElement.textContent.toLowerCase() === "true";
  }
  // Fallback or other logic if the element não existir
  console.warn(
    "Complex job toggle element not found, defaulting to true for calculations.",
  );
  return true; // Default to complex if cannot determine
}

export function calculateTotalRevenue() {
  const revenueTotals = {
    time: { estimate: 0, quote: 0, reality: 0 },
    materials: { estimate: 0, quote: 0, reality: 0 },
    adjustments: { estimate: 0, quote: 0, reality: 0 },
  };

  const gridTypes = ["Time", "Materials", "Adjustments"];
  const uiIsComplex = isComplex();

  sections.forEach((section) => {
    gridTypes.forEach((gridType) => {
      // 'reality' section always uses complex data model for calculations,
      // regardless of UI toggle for estimate/quote
      const useComplexDataForThisGrid = section === "reality" || uiIsComplex;

      const complexGridKey = `${section}${gridType}Table`;
      const simpleGridKey = `simple${capitalize(section)}${gridType}Table`;

      const gridKeyToRead = useComplexDataForThisGrid
        ? complexGridKey
        : simpleGridKey;
      const gridApi = window.grids?.[gridKeyToRead]?.api;

      if (gridApi) {
        gridApi.forEachNode((node) => {
          let rowRevenue = 0;
          if (useComplexDataForThisGrid) {
            // Logic for complex grids (or reality section)
            if (gridType === "Time") {
              // For complex TimeTable, revenue is derived from total_minutes and charge_out_rate
              // This assumes total_minutes is numeric (e.g., 120, not "120 (2.0 hours)")
              // The data loading functions (loadAdvJobTime) should ensure total_minutes is stored numerically if needed here,
              // or this calculation needs to parse it. For now, assume node.data.revenue is populated if complex.
              // If node.data.revenue is not directly available for complex time, calculate it:
              const totalMinutesStr = String(node.data.total_minutes);
              const totalMinutes = parseFloat(totalMinutesStr.split(" ")[0]) || 0; // Extracts number part
              const chargeRate = parseFloat(node.data.charge_out_rate) || 0;
              rowRevenue = (totalMinutes / 60) * chargeRate;
              // If 'revenue' field is already correctly populated in complex time grids, prefer that:
              // rowRevenue = parseFloat(node.data.revenue) || ((parseFloat(String(node.data.total_minutes).split(" ")[0]) || 0) / 60) * (parseFloat(node.data.charge_out_rate) || 0);

            } else if (gridType === "Materials") {
              rowRevenue = parseFloat(node.data.revenue) || 0; // 'revenue' field already calculated
            } else if (gridType === "Adjustments") {
              rowRevenue = parseFloat(node.data.price_adjustment) || 0; // price_adjustment is the revenue part
            }
          } else {
            // Logic for simple grids (estimate, quote, if uiIsComplex = false)
            if (gridType === "Time") {
              rowRevenue = parseFloat(node.data.value_of_time) || 0;
            } else if (gridType === "Materials") {
              rowRevenue = parseFloat(node.data.retail_price) || 0;
            } else if (gridType === "Adjustments") {
              rowRevenue = parseFloat(node.data.price_adjustment) || 0;
            }
          }
          const revenueTypeKey = gridType.toLowerCase(); // 'time', 'materials', 'adjustments'
          revenueTotals[revenueTypeKey][section] += rowRevenue;
        });
      }
    });
  });

  const revenueGrid = window.grids?.["revenueTable"];
  if (revenueGrid && revenueGrid.api) {
    revenueGrid.api.forEachNode((node, index) => {
      const data = node.data;
      switch (index) {
        case 0: // Total Time
          data.estimate = revenueTotals.time.estimate;
          data.quote = revenueTotals.time.quote;
          data.reality = revenueTotals.time.reality;
          break;
        case 1: // Total Materials
          data.estimate = revenueTotals.materials.estimate;
          data.quote = revenueTotals.materials.quote;
          data.reality = revenueTotals.materials.reality;
          break;
        case 2: // Total Adjustments
          data.estimate = revenueTotals.adjustments.estimate;
          data.quote = revenueTotals.adjustments.quote;
          data.reality = revenueTotals.adjustments.reality;
          break;
        case 3: // Total Project Cost
          data.estimate =
            revenueTotals.time.estimate +
            revenueTotals.materials.estimate +
            revenueTotals.adjustments.estimate;
          data.quote =
            revenueTotals.time.quote +
            revenueTotals.materials.quote +
            revenueTotals.adjustments.quote;
          data.reality =
            revenueTotals.time.reality +
            revenueTotals.materials.reality +
            revenueTotals.adjustments.reality;
          break;
      }
    });

    revenueGrid.api.refreshCells();
  }
}

export function calculateTotalCost() {
  const costTotals = { // Renamed from 'totals'
    time: { estimate: 0, quote: 0, reality: 0 },
    materials: { estimate: 0, quote: 0, reality: 0 },
    adjustments: { estimate: 0, quote: 0, reality: 0 },
  };

  const gridTypes = ["Time", "Materials", "Adjustments"];
  const uiIsComplex = isComplex();

  sections.forEach((section) => {
    gridTypes.forEach((gridType) => {
      const useComplexDataForThisGrid = section === "reality" || uiIsComplex;

      const complexGridKey = `${section}${gridType}Table`;
      const simpleGridKey = `simple${capitalize(section)}${gridType}Table`;

      const gridKeyToRead = useComplexDataForThisGrid
        ? complexGridKey
        : simpleGridKey;
      const gridApi = window.grids?.[gridKeyToRead]?.api;

      if (gridApi) {
        gridApi.forEachNode((node) => {
          let rowCost = 0;
          if (useComplexDataForThisGrid) {
            // Logic for complex grids (or reality section)
            if (gridType === "Time") {
              const totalMinutesStr = String(node.data.total_minutes);
              const totalMinutes = parseFloat(totalMinutesStr.split(" ")[0]) || 0; // Extracts number part
              const wageRate = parseFloat(node.data.wage_rate) || 0;
              rowCost = (totalMinutes / 60) * wageRate;
            } else if (gridType === "Materials") {
              const quantity = parseFloat(node.data.quantity) || 0;
              const unitCost = parseFloat(node.data.unit_cost) || 0;
              rowCost = quantity * unitCost;
            } else if (gridType === "Adjustments") {
              rowCost = parseFloat(node.data.cost_adjustment) || 0;
            }
          } else {
            // Logic for simple grids (estimate, quote, if uiIsComplex = false)
            if (gridType === "Time") {
              rowCost = parseFloat(node.data.cost_of_time) || 0;
            } else if (gridType === "Materials") {
              rowCost = parseFloat(node.data.material_cost) || 0;
            } else if (gridType === "Adjustments") {
              rowCost = parseFloat(node.data.cost_adjustment) || 0;
            }
          }
          const costTypeKey = gridType.toLowerCase();
          costTotals[costTypeKey][section] += rowCost;
        });
      }
    });
  });

  const costGrid = window.grids?.["costsTable"];
  if (costGrid && costGrid.api) {
    costGrid.api.forEachNode((node, index) => {
      const data = node.data;
      switch (index) {
        case 0: // Total Time
          data.estimate = costTotals.time.estimate;
          data.quote = costTotals.time.quote;
          data.reality = costTotals.time.reality;
          break;
        case 1: // Total Materials
          data.estimate = costTotals.materials.estimate;
          data.quote = costTotals.materials.quote;
          data.reality = costTotals.materials.reality;
          break;
        case 2: // Total Adjustments
          data.estimate = costTotals.adjustments.estimate;
          data.quote = costTotals.adjustments.quote;
          data.reality = costTotals.adjustments.reality;
          break;
        case 3: // Total Project Cost
          data.estimate =
            costTotals.time.estimate +
            costTotals.materials.estimate +
            costTotals.adjustments.estimate;
          data.quote =
            costTotals.time.quote +
            costTotals.materials.quote +
            costTotals.adjustments.quote;
          data.reality =
            costTotals.time.reality +
            costTotals.materials.reality +
            costTotals.adjustments.reality;
          break;
      }
    });
    costGrid.api.refreshCells();
  }
}

export function onCellKeyDown(params) {
  // For reality grids, or complex mode, add new rows on Enter
  const gridKey = params.context?.gridKey || "";
  const isComplex =
    document.getElementById("complex-job").textContent.toLowerCase() === "true";

  // Handle Enter key for both complex mode and reality grids
  if (
    params.event.key === "Enter" &&
    (isComplex || gridKey.includes("reality"))
  ) {
    const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
    if (isLastRow) {
      const newRow = createNewRow(params.context.gridType);
      if (newRow) {
        params.api.applyTransaction({ add: [newRow] });
        setTimeout(() => {
          params.api.setFocusedCell(params.rowIndex + 1, params.column.colId);
          params.api.startEditingCell({
            rowIndex: params.rowIndex + 1,
            colKey: params.column.colId,
          });
        }, 0);
        adjustGridHeight(params.api, gridKey);
      }
    }
  }
}

export function calculateRetailRate(costRate, markupRate) {
  // Ensure we're working with numbers
  costRate = parseFloat(costRate) || 0;
  markupRate = parseFloat(markupRate) || 0.2; // Default 20% markup

  // Calculate and ensure we return a number, not NaN
  const result = costRate + (costRate * markupRate);

  // Round to 2 decimal places to match database precision
  const roundedResult = Math.round(result * 100) / 100;

  console.log(`calculateRetailRate: ${costRate} + (${costRate} * ${markupRate}) = ${result} (rounded: ${roundedResult})`);
  return roundedResult;
}

export function fetchMaterialsMarkup(rowData) {
  // If already stored, return immediately
  if (rowData.materialsMarkup !== undefined) {
    console.log(`Using cached markup: ${rowData.materialsMarkup}`);
    return Promise.resolve(rowData.materialsMarkup);
  }

  console.log("Fetching materials markup from API...");
  return fetch("/api/company_defaults")
    .then((response) => response.json())
    .then((companyDefaults) => {
      rowData.materialsMarkup =
        parseFloat(companyDefaults.materials_markup) || 0.2;
      console.log(`Received markup from API: ${rowData.materialsMarkup}`);
      return rowData.materialsMarkup;
    })
    .catch((error) => {
      console.error("Error fetching company defaults:", error);
      rowData.materialsMarkup = 0.2; // Default to 20% on error
      return 0.2;
    });
}

export function getRetailRate(params) {
  if (params.data.unit_revenue !== undefined) {
    return params.data.unit_revenue; // Return stored value
  }

  // Fetch markup asynchronously, but return the last known value immediately
  fetchMaterialsMarkup(params.data).then((markupRate) => {
    if (!params.data.isManualOverride) {
      params.data.unit_revenue = calculateRetailRate(
        params.data.unit_cost,
        markupRate,
      );
      params.api.refreshCells({
        rowNodes: [params.node],
        columns: ["unit_revenue"],
        force: true,
      });
    }
  });

  return params.data.unit_revenue || 0; // Default fallback value
}

export function setRetailRate(params) {
  let newValue = parseFloat(params.newValue);
  let costRate = parseFloat(params.data.unit_cost) || 0;

  fetchMaterialsMarkup(params.data).then((markupRate) => {
    if (
      !isNaN(newValue) &&
      newValue !== calculateRetailRate(costRate, markupRate)
    ) {
      params.data.isManualOverride = true;
    }

    if (!params.data.isManualOverride) {
      params.data.unit_revenue = calculateRetailRate(costRate, markupRate);
    } else {
      params.data.unit_revenue = newValue;
    }

    params.api.refreshCells({
      rowNodes: [params.node],
      columns: ["unit_revenue"],
      force: true,
    });
  });

  console.log(`New Retail Rate calculated: ${params.data.unit_revenue}`);

  return true;
}

export function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function adjustGridHeight(gridApi, containerId) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.warn(`Grid container #${containerId} not found.`);
    return;
  }

  let rowCount = 0;
  gridApi.forEachNode(() => rowCount++);

  const rowHeight = gridApi.getSizesForCurrentTheme().rowHeight || 28;

  const header = container.querySelector(".ag-header");
  const headerHeight = header ? header.offsetHeight : 32;

  const maxHeight = 360;

  let desiredHeight = rowCount * rowHeight + headerHeight;

  if (desiredHeight > maxHeight) {
    desiredHeight = maxHeight;
  }

  container.style.height = `${desiredHeight}px`;
}

/**
 * Checks if there are any real values in the reality section and disables delete buttons if necessary
 */
export function checkRealityValues() {
  const realityGrids = [
    "realityTimeTable",
    "realityMaterialsTable",
    "realityAdjustmentsTable",
  ];
  let hasRealValues = false;

  realityGrids.forEach((gridKey) => {
    const gridData = window.grids[gridKey];
    if (gridData && gridData.api) {
      gridData.api.forEachNode((node) => {
        // Check for revenue or cost values > 0
        const revenue = parseFloat(node.data.revenue || 0);
        const cost = parseFloat(node.data.cost || 0);

        // For materials, also check quantity and unit_cost/unit_revenue
        const quantity = parseFloat(node.data.quantity || 0);
        const unitCost = parseFloat(node.data.unit_cost || 0);
        const unitRevenue = parseFloat(node.data.unit_revenue || 0);

        // For time entries, check minutes
        const minutes = parseFloat(node.data.total_minutes || 0);

        if (
          revenue > 0 ||
          cost > 0 ||
          (quantity > 0 && (unitCost > 0 || unitRevenue > 0)) ||
          minutes > 0
        ) {
          hasRealValues = true;
        }
      });
    }
  });

  // Disable delete buttons in reality section if there are real values
  if (hasRealValues) {
    const deleteButton = document.getElementById("delete-job-btn");
    if (deleteButton) {
      deleteButton.disabled = true;
    }
  }
}

export function checkJobAccepted() {
  console.log(
    "Job accepted?",
    document.getElementById("job_status").value === "accepted_quote",
  );
  const job_status = document.getElementById("job_status").value;
  const accepted =
    job_status === "accepted_quote"
      ? true
      : job_status === "completed"
        ? true
        : job_status === "archived"
          ? true
          : false;
  if (accepted) {
    lockQuoteGrids();
  }
}
