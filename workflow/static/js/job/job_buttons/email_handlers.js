import { renderMessages } from "/static/timesheet/js/timesheet_entry/messages.js"

/**
 * Centralizes all email-related logic, such as sending quotes and opening email clients.
 *
 * @param {string} jobId - The ID of the job/quote to be sent
 * @param {('gmail'|'outlook')} [provider='gmail'] - Email provider to use
 * @param {boolean} [contactOnly=false] - Whether to send only contact information
 * @returns {Promise<Object>} Response data from the email sending endpoint
 * @throws {Error} If email provider is not supported or if sending fails
 */
export async function sendQuoteEmail(
  jobId,
  provider = "gmail",
  contactOnly = false,
) {
  try {
    const endpoint = `/api/quote/${jobId}/send-email/?contact_only=${contactOnly}`;
    const response = await fetch(endpoint, { method: "POST" });
    const data = await response.json();

    if (data.success && data.mailto_url) {
      const email = data.mailto_url.match(/mailto:([^?]+)/)?.[1];
      const subject = encodeURIComponent(
        data.mailto_url.match(/subject=([^&]+)/)?.[1],
      );
      const body = encodeURIComponent(
        data.mailto_url.match(/body=([^&]+)/)?.[1],
      );

      let emailUrl = "";

      if (provider === "gmail") {
        emailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${email}&su=${subject}&body=${body}`;
      } else if (provider === "outlook") {
        emailUrl = `https://outlook.office.com/mail/deeplink/compose?to=${email}&subject=${subject}&body=${body}`;
      } else {
        throw new Error("Unsupported email provider.");
      }

      window.open(emailUrl, "_blank");
    } else if (!data.success) {
      console.error("Error sending email:", data.error);
    }

    return data;
  } catch (error) {
    renderMessages(
      [{ level: "error", message: `Error sending email: ${error.message}` }],
      "email-alert-container",
    );
    console.error("Error sending email:", error);
    throw error;
  }
}
