import { renderMessages } from './timesheet_entry/messages.js';
import { getCookie } from './timesheet_entry/utils.js';

/**
 * Initializes the Paid Absence Modal.
 * @param {string} modalId - The ID of the modal (e.g., "paidAbsenceModal").
 * @param {string} apiUrl - The URL to fetch the paid absence form.
 */
export function initializePaidAbsenceModal(modalId, apiUrl) {
    const modal = document.getElementById(modalId);
    if (!modal) {
        console.error(`Modal with ID '${modalId}' not found.`);
        return;
    }

    const paidAbsenceButton = document.querySelector('[data-bs-target="#' + modalId + '"]');
    const modalContainer = modal.querySelector('.modal-body');
    const form = modal.querySelector('form');

    if (!paidAbsenceButton || !modalContainer || !form) {
        console.error(`Paid Absence modal elements not found in '${modalId}'.`);
        return;
    }

    paidAbsenceButton.addEventListener('click', async () => {
        try {
            const response = await fetch(apiUrl, {
                method: "POST",
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: new URLSearchParams({ 'action': 'load_paid_absence_form' })
            });

            const data = await response.json();
            if (!data.success) {
                renderMessages(data.messages);
            }

            modalContainer.innerHTML = data.form_html;
        } catch (error) {
            console.error("Error loading paid absence form:", error);
            renderMessages([{ level: "error", message: "Failed to load form." }]);
        }
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const form = event.target;
        const formData = new FormData(form);

        formData.append('action', 'submit_paid_absence')

        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: new URLSearchParams(formData),
                action: 'submit_paid_absence'
            });

            const data = await response.json();
            if (data.success) {
                const modalElement = document.getElementById('paidAbsenceModal');
                const bootstrapModal = bootstrap.Modal.getInstance(modalElement);
                bootstrapModal.hide();
                
                renderMessages(data.messages);
            }

        } catch (error) {
            console.error("Error submitting paid absence:", error);
            renderMessages([{ level: "error", message: "Failed to submit paid absence." }]);
        }
    });
}
