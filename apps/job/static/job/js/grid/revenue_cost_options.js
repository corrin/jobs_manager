import { sections } from "./grid_initialization.js";
import {
  calculateTotalRevenue,
  calculateTotalCost,
  capitalize,
} from "./grid_utils.js";
import { currencyFormatter } from "./parsers.js";
import { Environment } from "/static/js/env.js";

// Grid options for Totals table (default 4 rows, autoHeight for proper resizing)
export function createRevenueGridOptions() {
  return {
    columnDefs: [
      { headerName: "Category", field: "category", editable: false },
      {
        headerName: "Estimate",
        field: "estimate",
        editable: false,
        valueFormatter: currencyFormatter,
      },
      {
        headerName: "Quote",
        field: "quote",
        editable: false,
        valueFormatter: currencyFormatter,
      },
      {
        headerName: "Reality",
        field: "reality",
        editable: false,
        valueFormatter: currencyFormatter,
      },
    ],
    rowData: [
      { category: "Total Time", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Materials", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Adjustments", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Project Revenue", estimate: 0, quote: 0, reality: 0 },
    ], // Default 4 rows
    domLayout: "autoHeight",
    rowHeight: 28,
    headerHeight: 32,
    suppressPaginationPanel: true,
    suppressHorizontalScroll: true,
    onGridReady: (params) => {
      window.grids["revenueTable"] = {
        gridInstance: params.api,
        api: params.api,
      };
      params.api.sizeColumnsToFit();

      calculateTotalRevenue();
    },
    onGridSizeChanged: (params) => {
      params.api.sizeColumnsToFit();
    },
    autoSizeStrategy: {
      type: "fitCellContents",
    },
  };
}

export function createCostGridOptions() {
  return {
    columnDefs: [
      { headerName: "Category", field: "category", editable: false },
      {
        headerName: "Estimate",
        field: "estimate",
        editable: false,
        valueFormatter: currencyFormatter,
      },
      {
        headerName: "Quote",
        field: "quote",
        editable: false,
        valueFormatter: currencyFormatter,
      },
      {
        headerName: "Reality",
        field: "reality",
        editable: false,
        valueFormatter: currencyFormatter,
      },
    ],
    rowData: [
      { category: "Total Time", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Materials", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Adjustments", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Project Cost", estimate: 0, quote: 0, reality: 0 },
    ], // Default 4 rows
    domLayout: "autoHeight",
    rowHeight: 28,
    headerHeight: 32,
    suppressPaginationPanel: true,
    suppressHorizontalScroll: true,
    onGridReady: (params) => {
      window.grids["costsTable"] = {
        gridInstance: params.api,
        api: params.api,
      };
      params.api.sizeColumnsToFit();

      calculateTotalCost();
    },
    onGridSizeChanged: (params) => {
      params.api.sizeColumnsToFit();
    },
    autoSizeStrategy: {
      type: "fitCellContents",
    },
  };
}

/**
 * Recalc cost_of_time e value_of_time for a simple time row
 */
export function recalcSimpleTimeRow(row) {
  const hours = parseFloat(row.hours) || 0;
  const wage = parseFloat(row.wage_rate) || 0;
  const charge = parseFloat(row.charge_out_rate) || 0;

  row.cost_of_time = hours * wage;
  row.value_of_time = hours * charge;
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

/**
 * Function that calculate totals (cost, retail) for each section (estimate, quote, reality)
 */
export function calculateSimpleTotals() {
  const isComplexJob = isComplex();

  const simpleTotals = {
    estimate: { cost: 0, retail: 0 },
    quote: { cost: 0, retail: 0 },
    reality: { cost: 0, retail: 0 },
  };

  if (Environment.isDebugMode()) {
    console.log("Starting calculateSimpleTotals calculation");
  }

  sections.forEach((section) => {
    if (Environment.isDebugMode()) {
      console.log(`Processing section: ${section}`);
    }

    // Reality is always complex
    const useComplex = section === "reality" || isComplexJob;

    // 1) Time
    processTimeGrid(section, useComplex, simpleTotals);

    // 2) Materials
    processMaterialsGrid(section, useComplex, simpleTotals);

    // 3) Adjustments
    processAdjustmentsGrid(section, useComplex, simpleTotals);
  });

  updateTotalsTables(simpleTotals);

  // Check if necessary grids exist before calculating overall totals
  const revenueGridExists = window.grids?.["revenueTable"]?.api;
  const costsGridExists = window.grids?.["costsTable"]?.api;

  if (revenueGridExists) {
    calculateTotalRevenue();
  }

  if (costsGridExists) {
    calculateTotalCost();
  }

  if (Environment.isDebugMode()) {
    console.log("Completed calculateSimpleTotals calculation", simpleTotals);
  }
}

// Added some aux functions
function processTimeGrid(section, useComplex, simpleTotals) {
  // For time grids, we need to distinguish between:
  // 1. Grid naming logic (reality vs estimate/quote)
  // 2. Processing logic (complex vs simple)
  const isRealitySection = section === "reality";
  const useComplexProcessing = useComplex; // This is the actual logic flag

  const timeGridKey = useComplexProcessing
    ? `${section}TimeTable`
    : `simple${capitalize(section)}TimeTable`;

  const timeApi = window.grids?.[timeGridKey]?.api;
  if (!timeApi) {
    if (Environment.isDebugMode()) {
      console.log(`Time grid not found: ${timeGridKey}`);
    }
    return;
  }

  const updatedTimeRows = [];

  timeApi.forEachNode((node) => {
    if (useComplexProcessing) {
      processComplexTimeRow(node.data, section, simpleTotals);
      return;
    }

    // Simple grid handling
    processSimpleTimeRow(node.data, section, simpleTotals, updatedTimeRows);
  });

  // Update only for simple grids
  if (!useComplexProcessing && updatedTimeRows.length > 0) {
    timeApi.applyTransaction({ update: updatedTimeRows });
  }

  if (Environment.isDebugMode()) {
    console.log(`Time totals for ${section} (useComplex: ${useComplexProcessing}):`, {
      cost: simpleTotals[section].cost,
      retail: simpleTotals[section].retail,
    });
  }
}

function processComplexTimeRow(data, section, simpleTotals) {
  // Handle total_minutes which might be stored as "120 (2.0 hours)" or just "120"
  let totalMinutes = 0;
  if (typeof data.total_minutes === 'string') {
    // Extract numeric part from strings like "120 (2.0 hours)"
    const match = data.total_minutes.match(/^(\d+(?:\.\d+)?)/);
    totalMinutes = match ? parseFloat(match[1]) : 0;
  } else {
    totalMinutes = parseFloat(data.total_minutes) || 0;
  }

  const wage = parseFloat(data.wage_rate) || 0;
  const charge = parseFloat(data.charge_out_rate) || 0;
  const hours = totalMinutes / 60;

  const cost = hours * wage;
  // For complex time grids, calculate revenue from hours and charge rate
  // Some grids might have a 'revenue' field, others calculate from total_minutes and charge_out_rate
  const retail = parseFloat(data.revenue) || (hours * charge);

  simpleTotals[section].cost += cost;
  simpleTotals[section].retail += retail;
}

function processSimpleTimeRow(data, section, simpleTotals, updatedTimeRows) {
  recalcSimpleTimeRow(data);
  updatedTimeRows.push(data);

  const cost = parseFloat(data.cost_of_time) || 0;
  const retail = parseFloat(data.value_of_time) || 0;
  simpleTotals[section].cost += cost;
  simpleTotals[section].retail += retail;
}

function processMaterialsGrid(section, isRealitySection, simpleTotals) {
  const matGridKey = isRealitySection
    ? `${section}MaterialsTable`
    : `simple${capitalize(section)}MaterialsTable`;

  const matApi = window.grids?.[matGridKey]?.api;
  if (!matApi) return;

  matApi.forEachNode((node) => {
    if (isRealitySection) {
      // Complex grid
      const cost =
        (parseFloat(node.data.unit_cost) || 0) *
        (parseFloat(node.data.quantity) || 0);
      const retail = parseFloat(node.data.revenue) || 0;
      simpleTotals[section].cost += cost;
      simpleTotals[section].retail += retail;
      return;
    }

    // Simple grid
    const cost = parseFloat(node.data.material_cost) || 0;
    const retail = parseFloat(node.data.retail_price) || 0;
    simpleTotals[section].cost += cost;
    simpleTotals[section].retail += retail;
  });

  if (Environment.isDebugMode()) {
    console.log(`Materials totals for ${section}:`, {
      cost: simpleTotals[section].cost,
      retail: simpleTotals[section].retail,
    });
  }
}

function processAdjustmentsGrid(section, isRealitySection, simpleTotals) {
  const adjGridKey = isRealitySection
    ? `${section}AdjustmentsTable`
    : `simple${capitalize(section)}AdjustmentsTable`;

  const adjApi = window.grids?.[adjGridKey]?.api;
  if (!adjApi) return;

  adjApi.forEachNode((node) => {
    const costAdj = parseFloat(node.data.cost_adjustment) || 0;
    const priceAdj = parseFloat(node.data.price_adjustment) || 0;

    simpleTotals[section].cost += costAdj;
    simpleTotals[section].retail += priceAdj;
  });

  if (Environment.isDebugMode()) {
    console.log(`Adjustments totals for ${section}:`, {
      cost: simpleTotals[section].cost,
      retail: simpleTotals[section].retail,
    });
  }
}

function updateTotalsTables(simpleTotals) {
  sections.forEach((section) => {
    const stKey = `simple${capitalize(section)}TotalsTable`;
    const stGrid = window.grids?.[stKey];
    if (!stGrid || !stGrid.api) return;

    const rowUpdates = [];
    stGrid.api.forEachNode((node) => {
      node.data.cost = simpleTotals[section].cost;
      node.data.retail = simpleTotals[section].retail;
      rowUpdates.push(node.data);
    });

    if (rowUpdates.length > 0) {
      stGrid.api.applyTransaction({ update: rowUpdates });
    }

    if (Environment.isDebugMode()) {
      console.log(`Final totals for ${section}:`, {
        cost: simpleTotals[section].cost,
        retail: simpleTotals[section].retail,
      });
    }
  });
}
