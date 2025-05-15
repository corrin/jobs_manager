import { sendQuoteEmail } from "./email_handlers.js";
import { renderMessages } from "/static/timesheet/js/timesheet_entry/messages.js"

/**
 * Manages modals that display instructions to users, such as the quote sending modal.
 * @module modal-handlers
 */

/**
 * @typedef {Object} Message
 * @property {'success'|'error'|'info'|'warning'} level - The message level
 * @property {string} message - The message text
 */

/**
 * Displays a modal for previewing and sending quotes to clients
 * @param {string} jobId - The ID of the job/quote to be sent
 * @param {string} [provider='gmail'] - The email provider to use
 * @param {boolean} [contactOnly=false] - If true, skips the modal and sends email directly
 * @returns {void}
 */
export function showQuoteModal(jobId, provider = "gmail", contactOnly = false) {
  if (contactOnly) {
    sendQuoteEmail(jobId, provider, true).catch((error) => {
      console.error("Error sending quote email:", error);
      renderMessages([
        { level: "error", message: "Failed to send quote email." },
      ]);
    });
    return;
  }

  const modalHtml = `
        <div class='modal fade' id='quoteModal' tabindex='-1' role='dialog' aria-labelledby='quoteModalLabel' aria-hidden='true'>
            <div class='modal-dialog' role='document'>
                <div class='modal-content'>
                    <div class='modal-header'>
                        <h5 class='modal-title' id='quoteModalLabel'>Preview and Send Quote</h5>
                        <button type='button' class='btn-close' data-bs-dismiss='modal' aria-label='Close'></button>
                    </div>
                    <div class='modal-body'>
                        <p>The quote has been generated. Please preview it in the opened tab and confirm if you'd like to send it to the client.</p>
                        
                        <div class='alert alert-info' role='alert'>
                            <p class='mb-1'>If the quote looks correct, please download the PDF from the opened tab and click 'Send Quote'.</p>
                            <hr>
                            <p class='mb-1'>This will open your email client where you can compose your message and attach the downloaded PDF</p>
                            <hr>
                            <p class='mb-0'><b>Please ensure the PDF is properly attached before sending the email to the client.</b></p>
                        </div>

                        <div id='email-alert-container' class='alert-container'></div>
                    </div>
                    <div class='modal-footer'>
                        <button type='button' class='btn btn-secondary' data-bs-dismiss='modal'>Close</button>
                        <button id='sendQuoteEmailButton' type='button' class='btn btn-primary'>Send Quote</button>
                    </div>
                </div>
            </div>
        </div>
    `;
  document.body.insertAdjacentHTML("beforeend", modalHtml);
  const quoteModal = new bootstrap.Modal(document.getElementById("quoteModal"));
  quoteModal.show();

  const sendQuoteButton = document.getElementById("sendQuoteEmailButton");
  // Remove duplicate event listeners if necessary:
  sendQuoteButton.replaceWith(sendQuoteButton.cloneNode(true));

  document
    .getElementById("sendQuoteEmailButton")
    .addEventListener("click", async () => {
      try {
        const data = await sendQuoteEmail(jobId, provider);
        if (data.success) {
          renderMessages(
            [
              {
                level: "success",
                message: "Email client opened successfully.",
              },
            ],
            "email-alert-container",
          );
        } else {
          renderMessages(
            [{ level: "error", message: "Failed to open email client." }],
            "email-alert-container",
          );
        }
      } catch (error) {
        renderMessages(
          [{ level: "error", message: `Error: ${error.message}` }],
          "email-alert-container",
        );
      }
    });
}
