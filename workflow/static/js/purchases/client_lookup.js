/**
 * Client/Supplier lookup component for Purchase Orders module
 * 
 * This JS module provides client (supplier) search functionality with suggestions.
 * It is used for purchase order forms.
 * 
 * Note: A similar version of this component exists at:
 * workflow/static/js/job/client_lookup.js
 * 
 * Make sure you update both files if you make any changes.
 *
 * Shared component for consistency across the application.
 */

import { debouncedAutosave } from "./purchase_order_autosave.js";

document.addEventListener("DOMContentLoaded", function () {
  const clientInput = document.getElementById("client_name");
  const suggestionsContainer = document.getElementById(
    "clientSuggestionsContainer",
  );

  if (!clientInput || !suggestionsContainer) {
    console.error("Client input field or suggestions container not found.");
    return;
  }

  // Clear Xero contact ID when client name is manually edited
  clientInput.addEventListener("input", function() {
    const clientXeroIdField = document.getElementById("client_xero_id");
    const clientIdField = document.getElementById("client_id");
    if (clientXeroIdField) {
      clientXeroIdField.value = "";
      clientIdField.value = "";
    }
  });

  // Add message event listener to handle client selection from child window
  window.addEventListener("message", function(event) {
    console.log("Received message:", event.data);
    
    // Handle messages from client selection window
    if (event.data && event.data.type === 'CLIENT_SELECTED') {
      console.log("Client selected, updating form fields:", event.data);
      
      // Get form fields
      const clientIdField = document.getElementById("client_id");
      const clientNameField = document.getElementById("client_name");
      const clientXeroIdField = document.getElementById("client_xero_id");
      
      // Update form fields with received data
      if (clientIdField) clientIdField.value = event.data.clientId;
      if (clientNameField) clientNameField.value = event.data.clientName;
      if (clientXeroIdField) clientXeroIdField.value = event.data.xeroContactId;
      
      console.log("Updated form fields:");
      console.log("- clientId:", clientIdField ? clientIdField.value : "field not found");
      console.log("- clientName:", clientNameField ? clientNameField.value : "field not found");
      console.log("- clientXeroId:", clientXeroIdField ? clientXeroIdField.value : "field not found");
      
      // Trigger autosave
      debouncedAutosave();
    }
  });

  function hideDropdown() {
    suggestionsContainer.innerHTML = "";
    suggestionsContainer.classList.add("d-none");
  }

  function showDropdown() {
    suggestionsContainer.classList.remove("d-none");
  }

  clientInput.addEventListener("input", function () {
    const query = clientInput.value.trim();

    if (query.length > 2) {
      fetch(`/api/client-search/?q=${encodeURIComponent(query)}`, {
        method: "GET",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "Content-Type": "application/json",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(
              "Network response was not ok: " + response.statusText,
            );
          }
          return response.json();
        })
        .then((data) => {
          displayClientSuggestions(data.results, query);
          showDropdown();
        })
        .catch((error) => {
          console.error("Error fetching client data:", error);
          hideDropdown();
        });
    } else {
      hideDropdown();
    }
  });

  // Global click event to close the dropdown
  document.addEventListener("click", function (event) {
    const isClickInsideInput = clientInput.contains(event.target);
    const isClickInsideContainer = suggestionsContainer.contains(event.target);

    if (!isClickInsideInput && !isClickInsideContainer) {
      suggestionsContainer.innerHTML = ""; // Clear suggestions
    }
  });

  // Prevent click inside the suggestions container from propagating
  suggestionsContainer.addEventListener("click", function (event) {
    event.stopPropagation(); // Prevents global listener from triggering
  });

  function displayClientSuggestions(clients, query) {
    suggestionsContainer.innerHTML = "";

    if (clients.length === 0) {
      const noResultsItem = document.createElement("div");
      noResultsItem.classList.add("suggestion-item");
      noResultsItem.textContent = "No clients found";
      suggestionsContainer.appendChild(noResultsItem);
    } else {
      clients.forEach((client) => {
        const suggestionItem = document.createElement("div");
        suggestionItem.classList.add("suggestion-item");
        suggestionItem.textContent = client.name;
        suggestionItem.dataset.clientId = client.id;

        suggestionItem.addEventListener("click", function () {
          clientInput.value = client.name;
          const clientIdField = document.getElementById("client_id");
          const clientNameField = document.getElementById("client_name");
          const clientXeroIdField = document.getElementById("client_xero_id");

          clientIdField.value = client.id;
          clientNameField.value = client.name;
          clientXeroIdField.value = client.xero_contact_id;

          if (!clientIdField.value || !clientNameField.value || !clientXeroIdField.value) {
            console.error(
              "Failed to update client fields in the form.",
            );
            renderMessages(
              [
                {
                  level: "error",
                  message:
                    "Failed to update client fields in the form.",
                },
              ],
              "job-details",
            );
          }

          debouncedAutosave();
          hideDropdown();
        });

        suggestionsContainer.appendChild(suggestionItem);
      });
    }

    const addNewOption = document.createElement("div");
    addNewOption.classList.add("suggestion-item", "add-new-client");
    addNewOption.textContent = `Add new client "${query}"`;
    addNewOption.addEventListener("click", function () {
      const newWindow = window.open(
        `/client/add/?name=${encodeURIComponent(query)}`,
        "_blank",
      );
      if (newWindow) {
        newWindow.focus();
      }

      debouncedAutosave();
      hideDropdown();
    });
    suggestionsContainer.appendChild(addNewOption);
  }

  document.addEventListener("click", function (event) {
    if (
      !clientInput.contains(event.target) &&
      !suggestionsContainer.contains(event.target)
    ) {
      hideDropdown();
    }
  });

  suggestionsContainer.addEventListener("click", function (event) {
    event.stopPropagation();
  });

  function getCsrfToken() {
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    return csrfToken ? csrfToken.value : "";
  }
}); 