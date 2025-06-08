// Main entry point for job editing functionality
import { initHistoricalNavigation } from "./historical_pricing_navigation.js";
import {
  initializeAdvancedGrids,
  initializeSimpleGrids,
} from "./grid/grid_initialization.js";
import { toggleGrid } from "./job_buttons/button_utils.js";
import { handleButtonClick } from "./job_buttons/button_handlers.js";
import "./import_quote.js";

// Initialize all modules when the document is ready
document.addEventListener("DOMContentLoaded", function () {
  // Initialize grid systems
  const isComplexGridActive =
    document.getElementById("toggleGridButton").checked;
  if (isComplexGridActive) {
    initializeAdvancedGrids();
  } else {
    initializeSimpleGrids();
  }

  // Initialize historical navigation
  initHistoricalNavigation();

  // Set up event listeners
  document.querySelectorAll("button[id]").forEach((button) => {
    button.addEventListener("click", handleButtonClick);
  });

  document
    .getElementById("toggleGridButton")
    .addEventListener("change", function () {
      toggleGrid("manual");
    });
});
