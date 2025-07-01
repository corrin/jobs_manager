/**
 * Client lookup component for Job module
 *
 * This JS module provides client search functionality with suggestions.
 * It is used for job creation/editing.
 *
 * Note: A virtually identical version of this component exists at:
 * workflow/static/js/purchases/client_lookup.js
 *
 * Make sure you update both files if you make any changes.
 *
 * Shared component for consistency across the application.
 */

import { debouncedAutosave } from "/static/job/js/edit_job_form_autosave.js";

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
  clientInput.addEventListener("input", function () {
    const clientXeroIdField = document.getElementById("client_xero_id");
    const clientIdField = document.getElementById("client_id");
    if (clientXeroIdField) {
      clientXeroIdField.value = "";
      clientIdField.value = "";
    }
  });
  // Add message event listener to handle client selection from child window
  window.addEventListener("message", function (event) {
    console.log("Received message:", event.data);

    // Handle messages from client selection window
    if (event.data && event.data.type === "CLIENT_SELECTED") {
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
      console.log(
        "- clientId:",
        clientIdField ? clientIdField.value : "field not found",
      );
      console.log(
        "- clientName:",
        clientNameField ? clientNameField.value : "field not found",
      );
      console.log(
        "- clientXeroId:",
        clientXeroIdField ? clientXeroIdField.value : "field not found",
      );

      // Clear contact fields when client changes
      clearContactFields();

      // Immediately refresh contacts and set default contact person
      refreshContactsAndSetDefault(event.data.clientId);
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
    const clientIdField = document.getElementById("client_id"); // Get client_id field
    const clientXeroIdField = document.getElementById("client_xero_id"); // Get client_xero_id field    // Clear client_id and xero_contact_id when client_name is manually changed
    if (clientIdField) clientIdField.value = "";
    if (clientXeroIdField) clientXeroIdField.value = "";

    if (query.length > 2) {
      fetch(`/clients/api/search/?q=${encodeURIComponent(query)}`, {
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

          if (clientIdField) clientIdField.value = client.id; // Ensure this is being set
          if (clientNameField) clientNameField.value = client.name; // Ensure this is being set
          if (clientXeroIdField) clientXeroIdField.value = client.xero_contact_id; // Ensure this is being set

          if (
            !clientIdField.value ||
            !clientNameField.value ||
            !clientXeroIdField.value
          ) {
            console.error("Failed to update client fields in the form.");
            renderMessages(
              [
                {
                  level: "error",
                  message: "Failed to update client fields in the form.",
                },
              ],
              "job-details",
            );
          }

          // Clear contact fields when client changes
          clearContactFields();

          // Immediately refresh contacts and set default contact person
          refreshContactsAndSetDefault(client.id);

          hideDropdown();
        });

        suggestionsContainer.appendChild(suggestionItem);
      });
    }

    const addNewOption = document.createElement("div");
    addNewOption.classList.add("suggestion-item", "add-new-client");
    addNewOption.textContent = `Add new client "${query}"`;
    addNewOption.addEventListener("click", function () {
      const currentClientName = clientInput.value.trim(); // Get current name from input
      const newWindow = window.open(
        // Pass current name to the add client form
        `/clients/add/?name=${encodeURIComponent(currentClientName)}`, // MODIFIED URL for adding new client
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

  // Clear contact fields when client changes
  function clearContactFields() {
    const contactFields = [
      'contact_id',
      'contact_display',
      'contact_person',
      'contact_phone',
      'contact_email'
    ];

    contactFields.forEach(fieldId => {
      const field = document.getElementById(fieldId);
      if (field) {
        field.value = '';
      }
    });
  }

  // Refresh contacts via API and set default contact person for the client
  async function refreshContactsAndSetDefault(clientId) {
    try {
      console.log(`Refreshing contacts for client ${clientId}`);

      // Fetch contacts for the new client
      const response = await fetch(`/clients/api/client/${clientId}/contacts/`);
      if (!response.ok) {
        throw new Error('Failed to fetch contacts');
      }

      const contacts = await response.json();
      console.log(`Found ${contacts.length} contacts for client ${clientId}`);

      // Find the primary contact
      const primaryContact = contacts.find(contact => contact.is_primary);

      if (primaryContact) {
        console.log(`Setting primary contact: ${primaryContact.name}`);

        // Update job contact fields
        const contactIdField = document.getElementById('contact_id');
        const contactDisplayField = document.getElementById('contact_display');
        const contactPersonField = document.getElementById('contact_person');
        const contactPhoneField = document.getElementById('contact_phone');
        const contactEmailField = document.getElementById('contact_email');

        if (contactIdField) contactIdField.value = primaryContact.id;
        if (contactDisplayField) {
          const displayValue = primaryContact.phone ?
            `${primaryContact.name} - ${primaryContact.phone}` :
            primaryContact.name;
          contactDisplayField.value = displayValue;
        }
        if (contactPersonField) contactPersonField.value = primaryContact.name;
        if (contactPhoneField) contactPhoneField.value = primaryContact.phone || '';
        if (contactEmailField) contactEmailField.value = primaryContact.email || '';

        // Trigger autosave for the contact changes
        if (contactIdField) {
          const event = new Event('change', { bubbles: true });
          contactIdField.dispatchEvent(event);
        }

        console.log(`Successfully set default contact: ${primaryContact.name}`);
      } else {
        console.log('No primary contact found for this client');
        // Contact fields are already cleared by clearContactFields()
      }

    } catch (error) {
      console.error('Error refreshing contacts:', error);
      // Show error message to user
      if (typeof renderMessages === 'function') {
        renderMessages([{
          level: 'error',
          message: 'Failed to load contacts for the selected client.'
        }], 'job-details');
      }
    }
  }
});
