/**
 * @fileoverview Grid initialization and management module for job pricing system
 * @module job_pricing_grids
 */

import { createNewRow, getGridData } from "../deserialize_job_pricing.js";
import { createSimpleTotalsGridOptions } from "./grid_options.js";
import { adjustGridHeight, capitalize } from "./grid_utils.js";

/** @constant {string[]} sections - Available pricing sections */
export const sections = ["estimate", "quote", "reality"];

/** @constant {string[]} workType - Types of work that can be priced */
export const workType = ["Time", "Materials", "Adjustments"];

/**
 * Initializes simple grid views
 * @param {Object} commonGridOptions - Common configuration options for all grids
 * @param {Object} timeGridOptions - Configuration specific to time grids
 * @param {Object} materialsGridOptions - Configuration specific to materials grids
 * @param {Object} adjustmentsGridOptions - Configuration specific to adjustments grids
 */
export function initializeSimpleGrids(
  commonGridOptions,
  timeGridOptions,
  materialsGridOptions,
  adjustmentsGridOptions,
) {
  sections.forEach((section) => {
    workType.forEach((work) => {
      const gridType = `Simple${work}Table`;
      const gridKey = `simple${capitalize(section)}${work}Table`;
      const gridElement = document.querySelector(`#${gridKey}`);
      if (!gridElement) {
        console.error(`Grid element not found for key: ${gridKey}`);
        return;
      }

      let specificGridOptions;
      switch (work) {
        case "Time":
          specificGridOptions = timeGridOptions;
          break;
        case "Materials":
          specificGridOptions = materialsGridOptions;
          break;
        case "Adjustments":
          specificGridOptions = adjustmentsGridOptions;
          break;
      }

      // Load initial rowData
      const rowData = getInitialRowData(section, gridType);

      // Build gridOptions
      const gridOptions = {
        ...specificGridOptions,
        context: {
          section,
          gridType,
          gridKey,
        },
        rowData,
      };

      agGrid.createGrid(gridElement, gridOptions);
    });

    // Now, we create the simple totals grids
    const gridType = `SimpleTotalsTable`;
    const gridKey = `simple${capitalize(section)}TotalsTable`;
    const gridElement = document.querySelector(`#${gridKey}`);

    if (!gridElement) {
      console.error(`Grid element not found for key: ${gridKey}`);
      return;
    }

    const totalsGridOptions = createSimpleTotalsGridOptions(gridKey);
    const gridOptions = {
      ...totalsGridOptions,
      context: {
        section,
        gridType,
        gridKey,
      },
    };

    agGrid.createGrid(gridElement, gridOptions);
  });
}

/**
 * Initializes advanced grid views with full functionality
 * @param {Object} commonGridOptions - Common configuration options for all grids
 * @param {Object} timeGridOptions - Configuration specific to time grids
 * @param {Object} materialsGridOptions - Configuration specific to materials grids
 * @param {Object} adjustmentsGridOptions - Configuration specific to adjustments grids
 */
export function initializeAdvancedGrids(
  commonGridOptions,
  timeGridOptions,
  materialsGridOptions,
  adjustmentsGridOptions,
) {
  window.grids = {}; // Stores all created grids

  sections.forEach((section) => {
    workType.forEach((work) => {
      createGrid(
        section,
        work,
        commonGridOptions,
        timeGridOptions,
        materialsGridOptions,
        adjustmentsGridOptions,
      );
    });
  });
}

/**
 * Creates an individual advanced grid
 * @private
 */
function createGrid(
  section,
  work,
  commonGridOptions,
  timeGridOptions,
  materialsGridOptions,
  adjustmentsGridOptions,
) {
  const gridType = `${work}Table`;
  const gridKey = `${section}${gridType}`;
  const gridElement = document.querySelector(`#${gridKey}`);
  if (!gridElement) {
    console.error(`Grid element not found for key: ${gridKey}`);
    return;
  }

  const specificGridOptions = getSpecificGridOptions(
    section,
    work,
    gridType,
    timeGridOptions,
    materialsGridOptions,
    adjustmentsGridOptions,
  );

  const rowData = getInitialRowData(section, gridType);

  const gridOptions = createGridOptions(
    section,
    gridType,
    gridKey,
    commonGridOptions,
    specificGridOptions,
    rowData
  );

  agGrid.createGrid(gridElement, gridOptions);
}

/**
 * Determines which gridOptions to use for Time, Materials or Adjustments
 * @private
 */
function getSpecificGridOptions(
  section,
  work,
  gridType,
  timeGridOptions,
  materialsGridOptions,
  adjustmentsGridOptions,
) {
  switch (gridType) {
    case "TimeTable":
      return getTimeTableOptions(section, timeGridOptions);
    case "MaterialsTable":
      return getMaterialsTableOptions(section, materialsGridOptions);
    case "AdjustmentsTable":
      return adjustmentsGridOptions;
    default:
      return {};
  }
}

/**
 * Adjusts TimeTable options for "reality" section (non-editable) or normal
 * @private
 */
function getTimeTableOptions(section, baseTimeGridOptions) {
  if (section === "reality") {
    // Create clone to avoid mutating the original
    const options = JSON.parse(JSON.stringify(baseTimeGridOptions));
    options.columnDefs.forEach((col) => {
      col.editable = false;
      if (col.field === "link") {
        col.cellRenderer = baseTimeGridOptions.columnDefs.find(
          (c) => c.field === "link",
        ).cellRenderer;
      }
    });
    // Remove columns without field
    options.columnDefs = options.columnDefs.filter((col) => col.field !== "");
    return options;
  }
  // Normal case
  const options = { ...baseTimeGridOptions };
  options.columnDefs = options.columnDefs.map((col) => {
    if (col.field === "link") {
      return { ...col, hide: true };
    }
    return col;
  });
  return options;
}

/**
 * Adjusts MaterialsTable options for "reality" section (non-editable) or normal
 * @private
 */
function getMaterialsTableOptions(section, baseMaterialsGridOptions) {
  if (section === "reality") {
    // Create clone to avoid mutating the original
    const options = JSON.parse(JSON.stringify(baseMaterialsGridOptions));
    options.columnDefs.forEach((col) => {
        col.editable = false; // Make all columns non-editable for reality
    });
    // Remove columns without a 'field' property (like the trash can column)
    options.columnDefs = options.columnDefs.filter(col => col.field);
    return options;
  }
  // Normal case (Estimate/Quote) - return base options as is
  return baseMaterialsGridOptions;
}

/**
 * Gets initial data for a specific grid, or creates row if empty
 * @private
 */
function getInitialRowData(section, gridType) {
  if (!latest_job_pricings_json) {
    console.error("latest_job_pricings_json not loaded.");
    throw new Error("Pricing data must be loaded before grid initialization");
  }

  const sectionData = latest_job_pricings_json[`${section}_pricing`];
  if (!sectionData) {
    // If it doesn't exist in JSON, create row
    if (Environment.isDebugMode()) {
      console.log(
        `[getInitialRowData] No section data found for ${section}, creating new row`,
      );
    }
    return [createNewRow(gridType)];
  }

  let rowData = getGridData(section, gridType);
  if (!rowData.length) {
    if (Environment.isDebugMode()) {
      console.log(
        `[getInitialRowData] No row data found for ${section} ${gridType}, creating new row`,
      );
    }
    rowData = [createNewRow(gridType)];
  }

  const gridKey = `${section}${gridType}`;
  const gridInstance = window.grids[gridKey];
  if (gridInstance) {
    if (Environment.isDebugMode()) {
      console.log(`Adjusting grid height for ${gridKey}`);
    }
    adjustGridHeight(gridInstance.api, `${gridKey}`);
  }

  return rowData;
}

/**
 * Combines gridOptions (common + specific) and sets context
 * @private
 */
function createGridOptions(
  section,
  gridType,
  gridKey,
  commonGridOptions,
  specificGridOptions,
  rowData=[],
) {
  return {
    ...commonGridOptions,
    ...specificGridOptions,
    context: { section, gridType, gridKey },
    rowData,
  };
}

/**
 * Creates summary tables (revenue and costs)
 */
export function createTotalTables(revenueGridOptions, costGridOptions) {
  const revenueTableEl = document.querySelector("#revenueTable");
  if (revenueTableEl) {
    try {
      agGrid.createGrid(revenueTableEl, revenueGridOptions);
    } catch (error) {
      console.error("Error initializing revenue table:", error);
    }
  } else {
    console.error("Revenue table element not found");
  }

  const costsTableEl = document.querySelector("#costsTable");
  if (costsTableEl) {
    try {
      agGrid.createGrid(costsTableEl, costGridOptions);
    } catch (error) {
      console.error("Error initializing costs table:", error);
    }
  } else {
    console.error("Costs table element not found");
  }
}

/**
 * Checks if all expected grids were created
 */
export function checkGridInitialization() {
  const expectedGridCount = sections.length * workType.length + 2;
  const actualGridCount = Object.keys(window.grids).length;

  if (actualGridCount < expectedGridCount) {
    console.error(
      `Not all grids were initialized. Expected ${expectedGridCount}, got ${actualGridCount}`,
    );
  }
}
