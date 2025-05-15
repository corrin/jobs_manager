import { addEventToTimeline } from "./button_utils.js";
import { renderMessages } from "/static/timesheet/js/timesheet_entry/messages.js";

/**
 * Responsible for saving new job events to the backend and adding the created event to the UI timeline.
 *
 * @param {string} jobId - The ID of the job to add the event to
 * @returns {void}
 */
export function handleSaveEventButtonClick(jobId) {
  const eventDescriptionField = document.getElementById("eventDescription");
  const description = eventDescriptionField.value.trim();

  if (!description) {
    renderMessages([
      { level: "error", message: "Please enter an event description." },
    ]);
    return;
  }

  const jobEventsList = document.querySelector(".timeline.list-group");
  const noEventsMessage = jobEventsList.querySelector(
    ".text-center.text-muted",
  );

  fetch(`/api/job-event/${jobId}/add-event/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
    },
    body: JSON.stringify({ description }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (!data.success) {
        renderMessages([
          { level: "error", message: data.error || "Failed to add an event." },
        ]);
        return;
      }

      if (noEventsMessage) {
        noEventsMessage.remove();
      }

      addEventToTimeline(data.event, jobEventsList);

      eventDescriptionField.value = "";
      const modal = bootstrap.Modal.getInstance(
        document.getElementById("addJobEventModal"),
      );
      modal.hide();
    })
    .catch((error) => {
      console.error("Error adding job event:", error);
      renderMessages([
        {
          level: "error",
          message: "Failed to add job event. Please try again.",
        },
      ]);
    });
}
