import { initializeWeekPicker } from "./week_picker.js";
import { initializePaidAbsenceModal } from "./paid_absence_modal.js";
import { checkQueryParam, toggleTableToIMS } from "./export_to_ims.js";

document.addEventListener("DOMContentLoaded", () => {
  console.log("Initializing...");
  initializeWeekPicker("weekPickerModal", "/timesheets/overview/{start_date}/");
  initializePaidAbsenceModal("paidAbsenceModal", window.location.href);

  const exportToIMSButton = document.getElementById("exportToIMS");

  checkQueryParam(exportToIMSButton);

  exportToIMSButton.addEventListener("click", toggleTableToIMS);
});
