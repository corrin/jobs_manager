/*
 * File Overview:
 * ----------------
 * This file manages the creation and interaction of grids using AG Grid. It includes
 * functionality for dynamically initializing multiple grids (time, materials, adjustments)
 * across various sections (e.g., estimate, quote, reality), and includes a special revenue grid.
 * Later we might add cost with the revenue grid.
 *
 * Key Interactions:
 * - Autosave Integration:
 *   The autosave functionality depends on grid changes triggering an event that captures
 *   the data across all relevant grids. It is crucial that the APIs for each grid are correctly
 *   initialized and stored in `window.grids` to ensure autosave has access to the necessary data.
 *
 * - AG Grid API Storage:
 *   Each grid API is stored in `window.grids` once the grid is initialized. This is critical
 *   for autosave, `calculateTotalRevenue()`, and other inter-grid operations. The revenue grid is
 *   also included here, as it is required for proper calculation and data refresh.
 *
 * - AG Grid Version Compatibility:
 *   Ensure that changes align with AG Grid version 33.0.2. Be aware of deprecated properties
 *   and avoid using older APIs that may not be compatible with this version.
 *
 * Important Notes:
 * - The `onGridReady` function, inherited from `commonGridOptions`, is responsible for storing
 *   each grid's API in `window.grids`. Do not modify the initialization logic to exclude this step.
 * - Each grid API is crucial for the autosave mechanism. Breaking or missing the correct API
 *   initialization may lead to unexpected errors or the autosave failing silently.
 * - Maintain a consistent approach to API storage and avoid changes that bypass or duplicate
 *   API handling in `onGridReady`.
 */

// Grid column definitions
import { createTrashCanColumn } from "./grid/columns.js";

// Grid options creators
import {
  createCommonGridOptions,
  createAdvancedTimeGridOptions,
  createAdvancedMaterialsGridOptions,
  createAdvancedAdjustmentsGridOptions,
  createSimpleTimeGridOptions,
  createSimpleMaterialsGridOptions,
  createSimpleAdjustmentsGridOptions,
  createSimpleTotalsGridOptions,
} from "./grid/grid_options.js";

// Revenue and cost grid options
import {
  createRevenueGridOptions,
  createCostGridOptions,
} from "./grid/revenue_cost_options.js";

// Grid initialization and management
import {
  initializeAdvancedGrids,
  initializeSimpleGrids,
  createTotalTables,
  checkGridInitialization,
} from "./grid/grid_initialization.js";

// Grid calculations
import { calculateTotalRevenue, calculateTotalCost, checkRealityValues, checkJobAccepted, updateGridOverflowClasses } from "./grid/grid_utils.js";

// Button Handler
import { handleButtonClick } from "./job_buttons/button_handlers.js";

import { loadJobDetails } from "./job_details_loader.js";
import { toggleGrid, togglePricingType } from "./job_buttons/button_utils.js";


document.addEventListener("DOMContentLoaded", function () {
  loadJobDetails();

  const trashCanColumn = createTrashCanColumn();

  // Advanced grid creation
  const commonGridOptions = createCommonGridOptions();
  const advancedTimeGridOptions = createAdvancedTimeGridOptions(
    commonGridOptions,
    trashCanColumn,
  );
  const advancedMaterialsGridOptions = createAdvancedMaterialsGridOptions(
    commonGridOptions,
    trashCanColumn,
  );
  const advancedAdjustmentsGridOptions = createAdvancedAdjustmentsGridOptions(
    commonGridOptions,
    trashCanColumn,
  );

  // Simple grid creation
  const simpleTimeGridOptions = createSimpleTimeGridOptions(
    commonGridOptions,
    trashCanColumn,
  );
  const simpleMaterialsGridOptions = createSimpleMaterialsGridOptions(
    commonGridOptions,
    trashCanColumn,
  );
  const simpleAdjustmentsGridOptions = createSimpleAdjustmentsGridOptions(
    commonGridOptions,
    trashCanColumn,
  );

  initializeAdvancedGrids(
    commonGridOptions,
    advancedTimeGridOptions,
    advancedMaterialsGridOptions,
    advancedAdjustmentsGridOptions,
  );

  initializeSimpleGrids(
    commonGridOptions,
    simpleTimeGridOptions,
    simpleMaterialsGridOptions,
    simpleAdjustmentsGridOptions,
  );

  // Grid options for Totals table (default 4 rows, autoHeight for proper resizing)
  const revenueGridOptions = createRevenueGridOptions();
  const costGridOptions = createCostGridOptions();

  createTotalTables(revenueGridOptions, costGridOptions);

  setTimeout(checkGridInitialization, 3000);
  setTimeout(calculateTotalRevenue, 1000);
  setTimeout(calculateTotalCost, 1000);
  setTimeout(checkRealityValues, 1500);
  setTimeout(checkJobAccepted, 2000);
  setTimeout(updateGridOverflowClasses, 2500);

  const isComplexJob = document.getElementById("complex-job").textContent.toLowerCase() === 'true';
  toggleGrid(isComplexJob ? "complex" : "simple");
  
  document.body.addEventListener("click", handleButtonClick);
  document.getElementById('pricingTypeDropdown').addEventListener('change', (event) => togglePricingType(event));
  document.getElementById("job_status").addEventListener('change', checkJobAccepted);
  console.log("Checking grids before checking job accepted",window.grids);
});
