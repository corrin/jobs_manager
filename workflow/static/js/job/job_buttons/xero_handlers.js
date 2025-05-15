import { renderMessages } from "/static/timesheet/js/timesheet_entry/messages.js"
import { capitalize } from "../grid/grid_utils.js";

/**
 * Creates, deletes and manages documents linked to Xero (invoices, quotes, etc.).
 * Also updates UI elements that show quote or invoice status.
 *
 * @param {string} jobId - The ID of the job to create a document for
 * @param {('invoice'|'quote')} type - The type of document to create
 * @returns {void}
 */
export function createXeroDocument(jobId, type, buttonEl) {
  console.log(`Creating Xero ${type} for job ID: ${jobId}`);

  const originalText = buttonEl.innerHTML;
  buttonEl.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${type === 'invoice' ? 'Invoicing' : 'Quoting'}...`;

  if (!jobId) {
    console.error("Job ID is missing");
    renderMessages([{ level: "error", message: "Job id is missing!" }]);
    return;
  }

  const endpoint =
    type === "invoice"
      ? `/api/xero/create_invoice/${jobId}`
      : `/api/xero/create_quote/${jobId}`;

  fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
    },
  })
    .then(async (response) => {
      if (!response.ok) {
        return response.json().then((data) => {
          if (data.redirect_to_auth) {
            renderMessages([
              {
                level: "error",
                message:
                  "Your Xero session ended. Redirecting you to Xero login...",
              },
            ]);
            // Redirect if needed
            return;
          }
          throw new Error(data.message || "Failed to create document.");
        });
      }
      return response.json();
    })
    .then((data) => {
      if (!data || !data.success) {
        console.error("Document creation failed:", data?.messages);
        renderMessages(
          data?.messages || [
            { level: "error", message: "Failed to create document." },
          ],
        );
        return;
      }

      console.log(`${type} created successfully with Xero ID: ${data.xero_id}`);
      handleDocumentButtons(type, data.invoice_url || data.quote_url, "POST");

      const documentSummary = `
            <div class='card'>
                <div class='card-header bg-success text-white'>
                    ${type === "invoice" ? "Invoice" : "Quote"} Created Successfully
                </div>
                <div class='card-body'>
                    <p><strong>Xero ID:</strong> ${data.xero_id}</p>
                    <p><strong>Client:</strong> ${data.client}</p>
                    ${data.invoice_url ? `<a href='${data.invoice_url}' target='_blank' class='btn btn-info'>Go to Xero</a>` : ""}
                    ${data.quote_url ? `<a href='${data.quote_url}' target='_blank' class='btn btn-info'>Go to Xero</a>` : ""}
                    <div class="alert alert-info mt-3">
                        <small>If the button above doesn't work, search by Xero ID <strong>${data.xero_id}</strong> in Xero.</small>
                    </div>
                </div>
            </div>
        `;
      document.getElementById("alert-modal-body").innerHTML = documentSummary;
      new bootstrap.Modal(document.getElementById("alert-container")).show();
    })
    .catch((error) => {
      console.error("Error creating Xero document:", error);
      renderMessages([
        { level: "error", message: `An error occurred: ${error.message}` },
      ]);
    })
    .finally(() => {
      buttonEl.innerHTML = originalText;
    });
}

/**
 * Handles the state of document-related buttons and UI elements
 *
 * @param {('invoice'|'quote')} type - The type of document being handled
 * @param {string|null} online_url - The URL to the document in Xero
 * @param {('POST'|'DELETE')} method - The action being performed
 * @returns {void}
 */
export function handleDocumentButtons(type, online_url, method) {
  const documentButton = document.getElementById(
    type === "invoice" ? "invoiceJobButton" : "quoteJobButton",
  );
  const statusCheckbox = document.getElementById(
    type === "invoice" ? "invoiced_checkbox" : "quoted_checkbox",
  );
  const deleteButton = document.getElementById(
    type === "invoice" ? "deleteInvoiceButton" : "deleteQuoteButton",
  );
  const xeroLink = document.getElementById(
    type === "invoice" ? "invoiceUrl" : "quoteUrl",
  );

  if (online_url) {
    xeroLink.href = online_url;
  }

  switch (method) {
    case "POST":
      documentButton.disabled = true;
      deleteButton.style.display = "inline-block";
      statusCheckbox.disabled = false;
      statusCheckbox.checked = true;
      xeroLink.style.display = "inline-block";
      break;

    case "DELETE":
      documentButton.disabled = false;
      deleteButton.style.display = "none";
      statusCheckbox.disabled = true;
      statusCheckbox.checked = false;
      xeroLink.style.display = "none";
      break;
  }
}

/**
 * Deletes a document from Xero
 *
 * @param {string} jobId - The ID of the job whose document should be deleted
 * @param {('invoice'|'quote')} type - The type of document to delete
 * @returns {void}
 */
export function deleteXeroDocument(jobId, type, buttonEl) {
  console.log(`Deleting Xero ${type} for job ID: ${jobId}`);

  if (!confirm(`Are you sure you want to delete this ${type}?`)) {
    return;
  }

  const originalText = buttonEl.innerHTML;
  buttonEl.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...`;

  const endpoint =
    type === "invoice"
      ? `/api/xero/delete_invoice/${jobId}`
      : `/api/xero/delete_quote/${jobId}`;

  fetch(endpoint, {
    method: "DELETE",
    headers: {
      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
    },
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((data) => {
          if (data.redirect_to_auth) {
            // Redirect if needed
            return;
          }
          throw new Error(data.message || "Failed to delete document.");
        });
      }
      return response.json();
    })
    .then((data) => {
      if (!data || !data.success) {
        renderMessages(
          data?.messages || [
            { level: "error", message: "Failed to delete document." },
          ],
        );
        return;
      }
      handleDocumentButtons(type, null, "DELETE");
      renderMessages(data.messages || [ { "level": "success", "message":  `${capitalize(type)} deleted successfully!` } ], "toast-container");
    })
    .catch((error) => {
      console.error("Error deleting Xero document:", error);
      renderMessages([
        { level: "error", message: `An error occurred: ${error.message}` },
      ], "toast-container");
    })
    .finally(() => {
      buttonEl.innerHTML = originalText;
    });;
}
