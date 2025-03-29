import { renderMessages } from "./timesheet_entry/messages.js";
import { getCookie } from "./timesheet_entry/utils.js";

/**
 * Initializes the Paid Absence Modal.
 * @param {string} modalId - The ID of the modal (e.g., "paidAbsenceModal").
 * @param {string} apiUrl - The URL to fetch the form.
 */
export function initializePaidAbsenceModal(modalId, apiUrl) {
  const modal = document.getElementById(modalId);
  if (!modal) {
    console.error(`Modal with ID '${modalId}' not found.`);
    return;
  }

  const paidAbsenceButton = document.querySelector(
    '[data-bs-target="#' + modalId + '"]'
  );
  const modalContainer = modal.querySelector(".modal-body");

  if (!paidAbsenceButton || !modalContainer) {
    console.error(`Modal elements not found in '${modalId}'.`);
    return;
  }

  // Load the form when the button is clicked
  paidAbsenceButton.addEventListener("click", async () => {
    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: new URLSearchParams({ action: "load_paid_absence_form" }),
      });

      const data = await response.json();
      if (!data.success) {
        renderMessages(data.messages);
        return;
      }

      // Insert the form HTML
      modalContainer.innerHTML = data.form_html;
      
      // Now that the form exists, add the event listener
      setupFormSubmissionListener(modal, apiUrl);
      
    } catch (error) {
      console.error("Error loading form:", error);
      renderMessages([{ level: "error", message: "Failed to load form." }]);
    }
  });
}

/**
 * Configure the form submission listener
 */
function setupFormSubmissionListener(modal, apiUrl) {
  const form = modal.querySelector("form#paid-absence-form");
  
  if (!form) {
    console.error("Form not found after loading");
    return;
  }
  
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    
    const formData = new FormData(form);
    formData.append("action", "submit_paid_absence");
    
    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: new URLSearchParams(formData),
      });
      
      const data = await response.json();
      
      // Show success or error messages
      renderMessages(data.messages || [{ level: "error", message: "Invalid server response" }]);
      
      if (data.success) {
        // Close the modal
        const modalInstance = bootstrap.Modal.getInstance(modal);
        modalInstance.hide();
        
        // If necessary, reload the page after success
        if (data.reload) {
          window.location.reload();
        }
      }
    } catch (error) {
      console.error("Error submitting form:", error);
      renderMessages([{ level: "error", message: "Failed to submit form." }]);
    }
  });
}
