/**
 * Renders dynamic messages in the template's message container.
 * @param {Array} messages - List of messages in the format [{level: "success|error|info", message: "Message"}].
 */
function renderMessages(messages) {
    const alertContainer = document.querySelector('.alert-container');
    if (!alertContainer) {
        console.error('Alert container not found.');
        return;
    }

    // Clear old messages
    alertContainer.innerHTML = '';

    // Add new messages
    messages.forEach(msg => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${msg.level} alert-dismissible fade show mt-1`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${msg.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        alertContainer.appendChild(alertDiv);

        // Add fade out effect after 1 second
        setTimeout(() => {
            alertDiv.classList.remove('show');
            alertDiv.classList.add('fade');
            setTimeout(() => {
                alertDiv.remove();
            }, 150); // Wait for fade animation to complete
        }, 1500);
    });
}

// Make the function globally accessible
window.renderMessages = renderMessages;
