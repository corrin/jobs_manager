import { Environment } from "/static/js/env.js";

const sentMessages = new Set();

const MESSAGE_TIMEOUT = 15000;
const messageTimestamps = new Map();

function canShowMessage(messageKey) {
  if (Environment.isDebugMode()) {
    console.log("Checking message:", messageKey);
    console.log("Message already sent:", sentMessages.has(messageKey));
  }

  if (!sentMessages.has(messageKey)) {
    if (Environment.isDebugMode()) {
      console.log("Message not sent before, allowing");
    }
    messageTimestamps.set(messageKey, Date.now());
    sentMessages.add(messageKey);
    return true;
  }

  const lastShown = messageTimestamps.get(messageKey);
  const now = Date.now();
  const timeDiff = now - lastShown;

  if (Environment.isDebugMode()) {
    console.log("Last shown:", lastShown);
    console.log("Current time:", now);
    console.log("Time difference:", timeDiff);
    console.log("Message timeout:", MESSAGE_TIMEOUT);
  }

  if (timeDiff >= MESSAGE_TIMEOUT) {
    if (Environment.isDebugMode()) {
      console.log("Timeout exceeded, clearing message and allowing");
    }
    messageTimestamps.set(messageKey, Date.now());
    return true;
  }

  if (Environment.isDebugMode()) {
    console.log("Message blocked - too soon to show again");
  }

  return false;
}

function createToastContainer() {
  const container = document.createElement("div");
  container.className = "toast-container position-fixed top-0 end-0 p-3";
  container.style.zIndex = "1070";
  document.body.appendChild(container);
  return container;
}

/**
 * Renders dynamic messages in a modal or as toast notifications
 * @param {Array} messages - List of messages in the format [{level: "success|error|info", message: "Message"}]
 * @param {string} [containerId] - If provided, shows toast notifications instead of modal
 * @param {Boolean} [cooldown] - If provided, defines a cooldown for the message to be displayed. Defaults to true.
 */
export function renderMessages(messages, containerId = null, cooldown = true) {
  let alertContainer;
  let alertContainerModal = false;
  let modal;

  // Modal logic for when no containerId is provided
  if (!containerId) {
    alertContainer = document.getElementById("alert-modal-body");
    alertContainerModal = true;
    const modalContainer = document.getElementById("alert-container");
    if (!modalContainer || !alertContainerModal) {
      console.error("Alert modal container or body not found.");
      return;
    }
    modal = new bootstrap.Modal(modalContainer);
    modal.show();
    alertContainer.innerHTML = "";
  }

  // Toast container logic for when containerId is provided
  const toastContainer = containerId
    ? document.querySelector(".toast-container") || createToastContainer()
    : null;

  messages.forEach((msg) => {
    const messageKey = `${msg.level}:${msg.message}`;

    if (!canShowMessage(messageKey) && cooldown) return;

    msg.level = msg.level === "error" ? "danger" : msg.level;

    if (containerId) {
      // Toast notification logic
      const toastElement = document.createElement("div");
      toastElement.className = `toast border-0 border-${msg.level}`;
      toastElement.setAttribute("role", "alert");
      toastElement.setAttribute("aria-live", "assertive");
      toastElement.setAttribute("aria-atomic", "true");

      toastElement.innerHTML = `
        <div class="toast-header bg-${msg.level} text-white">
          <strong class="me-auto">${msg.level.charAt(0).toUpperCase() + msg.level.slice(1)}</strong>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
          ${msg.message}
        </div>
      `;

      toastContainer.appendChild(toastElement);

      const toast = new bootstrap.Toast(toastElement, {
        animation: true,
        autohide: true,
        delay: 5000,
      });

      toast.show();

      toastElement.addEventListener("hidden.bs.toast", () => {
        setTimeout(() => toastElement.remove(), 150);
      });
    } else {
      // Modal alert logic
      const alertDiv = document.createElement("div");
      alertDiv.className = `alert alert-${msg.level} alert-dismissible fade show mt-1`;
      alertDiv.role = "alert";
      alertDiv.innerHTML = `
        ${msg.message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      `;
      alertContainer.appendChild(alertDiv);

      setTimeout(() => {
        alertDiv.classList.remove("show");
        alertDiv.classList.add("fade");
        setTimeout(() => {
          alertDiv.remove();
          if (modal && alertContainer.children.length === 0) {
            modal.hide();
          }
        }, 150);
      }, 5000);
    }
  });
}

// Ensure the window object is available before assigning
if (typeof window !== "undefined") {
  window.renderMessages = renderMessages;
}