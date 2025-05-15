// Button handlers
import {
  getJobIdFromUrl,
  toggleGrid,
  lockQuoteGrids,
  updateJobStatus,
} from "./button_utils.js";
import { showQuoteModal } from "./modal_handlers.js";
import { handleSaveEventButtonClick } from "./job_events.js";
import { createXeroDocument, deleteXeroDocument } from "./xero_handlers.js";

// External functions
import {
  copyEstimateToQuote,
  debouncedAutosave,
  handlePrintWorkshop,
} from "../edit_job_form_autosave.js";
import {
  calculateTotalCost,
  calculateTotalRevenue,
} from "../grid/grid_utils.js";

/**
 * Handles all button clicks on the page by identifying which action to trigger
 * and calling the corresponding module functions.
 *
 * @param {Event} event - The click event object
 * @returns {void}
 */
export function handleButtonClick(event) {
  console.log("Button clicked:", event.target.id);
  const buttonId = event.target.id;
  const jobId = getJobIdFromUrl();
  const button = document.getElementById(buttonId);

  switch (buttonId) {
    case "copyEstimateToQuote":
      copyEstimateToQuote();
      calculateTotalCost();
      calculateTotalRevenue();
      break;

    case "quoteJobButton":
      createXeroDocument(jobId, "quote", button);
      break;

    case "deleteQuoteButton":
      deleteXeroDocument(jobId, "quote", button);
      break;

    case "invoiceJobButton":
      createXeroDocument(jobId, "invoice", button);
      break;

    case "deleteInvoiceButton":
      deleteXeroDocument(jobId, "invoice", button);
      break;

    case "printWorkshopButton":
      handlePrintWorkshop();
      break;

    case "acceptQuoteButton":
      lockQuoteGrids();
      updateJobStatus(jobId);
      break;

    case "contactClientButton":
      showQuoteModal(jobId, "gmail", true);
      break;

    case "saveEventButton":
      handleSaveEventButtonClick(jobId);
      break;

    case "toggleGridButton":
      toggleGrid("manual");

    default:
      break;
  }
}
