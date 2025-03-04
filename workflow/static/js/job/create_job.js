document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('createJobForm');
    const saveButton = document.getElementById('saveButton');
    const cancelButton = document.getElementById('cancelButton');

    function validateForm() {
        const clientXeroId = document.getElementById('client_xero_id').value;
        const jobName = document.getElementById('name').value;

        if (!clientXeroId || !jobName) {
            alert('Please fill in all required fields:\n- Client\n- Job Name');
            return false;
        }
        return true;
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        saveButton.disabled = true;
        saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/jobs/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const result = await response.json();
            window.location.href = `/jobs/${result.job_id}/edit/`;
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while saving the job. Please try again.');
        } finally {
            saveButton.disabled = false;
            saveButton.innerHTML = 'Save & Continue';
        }
    });

    cancelButton.addEventListener('click', function() {
        if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
            window.location.href = '/jobs/';
        }
    });

    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}); 