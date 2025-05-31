/**
 * Linked Quote Functionality
 * 
 * This script handles the creation of linked quotes from the master template.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get the create linked quote button
    const createLinkedQuoteBtn = document.getElementById('create-linked-quote-btn');
    
    if (createLinkedQuoteBtn) {
        createLinkedQuoteBtn.addEventListener('click', createLinkedQuote);
    }
});

/**
 * Create a linked quote for the current job
 */
function createLinkedQuote() {
    // Get the job ID from the hidden input
    const jobId = document.getElementById('job_id').value;
    
    // Disable the button and show loading state
    const button = document.getElementById('create-linked-quote-btn');
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';
    
    // Make the API call to create the linked quote
    fetch(`/api/job/${jobId}/create-linked-quote/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Get the button and its parent container
            const button = document.getElementById('create-linked-quote-btn');
            const buttonContainer = button.parentElement;
            
            // Replace the button with a link to the new quote
            buttonContainer.innerHTML = `
                <a href="${data.quote_url}" target="_blank" class="btn btn-primary">
                    <i class="fas fa-external-link-alt"></i> Edit Quote
                </a>
                <input type="hidden" id="linked_quote" name="linked_quote" value="${data.quote_url}">
            `;
            
            // Show a success message
            showAlert('success', 'Linked quote created successfully!');
        } else {
            // Show an error message
            button.disabled = false;
            button.innerHTML = originalText;
            showAlert('danger', `Error: ${data.error}`);
        }
    })
    .catch(error => {
        // Show an error message
        button.disabled = false;
        button.innerHTML = originalText;
        showAlert('danger', `Error: ${error.message}`);
    });
}

/**
 * Show an alert message in the job details alert container
 */
function showAlert(type, message) {
    const alertContainer = document.getElementById('job-details');
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => {
            alertContainer.removeChild(alert);
        }, 150);
    }, 5000);
}