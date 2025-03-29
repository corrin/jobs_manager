/**
 * Purchase form autosave functionality
 * 
 * Provides debounced autosave functionality for purchase forms
 * Similar to the implementation in the job module
 */

// Import debounce utility if it's in a separate file, or define it here
function debounce(func, wait) {
  let timeout;
  return function(...args) {
    const context = this;
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(context, args), wait);
  };
}

// Main autosave function
function autosaveData() {
  console.log("Autosaving purchase data...");
  
  // Get form data
  const form = document.getElementById("purchase-form");
  if (!form) {
    console.error("Purchase form not found");
    return;
  }
  
  const formData = new FormData(form);
  const purchaseId = document.getElementById("purchase_id").value;
  
  // Send data to server
  fetch(`/api/purchases/${purchaseId}/autosave/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCsrfToken(),
    },
    body: formData,
  })
    .then(response => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then(data => {
      console.log("Purchase autosave successful:", data);
      // Optional: Update UI to indicate successful save
    })
    .catch(error => {
      console.error("Purchase autosave error:", error);
      // Optional: Show error message
    });
}

// Debounced version of the autosave function
export const debouncedAutosave = debounce(function () {
  console.log("Debounced purchase autosave called");
  autosaveData();
}, 1000);

// Helper function to get CSRF token
function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]').value;
} 