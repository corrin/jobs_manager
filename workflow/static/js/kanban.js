console.log('kanban.js load started');

document.addEventListener('DOMContentLoaded', function () {
    console.log('Script loaded and DOM fully loaded');

    fetchStatusValues();  // Fetch statuses dynamically

    // Initialize search functionality
    document.getElementById('search').addEventListener('input', filterJobs);
});

function fetchStatusValues() {
    // console.log('Fetching status values');
    fetch('/api/fetch_status_values/')
        .then(response => response.json())
        .then(statuses => {
            // console.log('Received data:', statuses);
            if (statuses && typeof statuses === 'object') {  // No need to check if it's an array
                // console.log('Status choices:', statuses);
                loadAllColumns(statuses);  // Pass the dictionary directly
            } else {
                console.error('Unexpected data structure:', statuses);
            }
        })
        .catch(error => console.error('Error fetching status values:', error));
}


function loadAllColumns(statuses) {
    // console.log('Loading all columns with statuses:', statuses);
    if (!statuses || typeof statuses !== 'object') {
        console.error('Invalid statuses data:', statuses);
        return;
    }
    for (const status_key in statuses) {
        if (statuses.hasOwnProperty(status_key)) {
            // console.log('Processing status:', status_key, 'with label:', statuses[status_key]);
            fetchJobs(status_key);
        }
    }
}


function fetchJobs(status) {
    fetch(`/kanban/fetch_jobs/${status}/`)
        .then(response => response.json())
        .then(data => {
            const container = document.querySelector(`#${status} .job-list`);
            if (!container) {
                console.error(`Container not found for status: ${status}`);
                return;  // Exit if the container is null
            }

            container.innerHTML = ''; // Clear existing cards

            // Only add job cards if jobs are present
            data.jobs.forEach(job => {
                let card = createJobCard(job);
                container.appendChild(card);
            });

            // Initialize SortableJS for drag-and-drop functionality
            new Sortable(container, {
                group: 'shared',
                animation: 150,
                ghostClass: 'job-card-ghost',
                chosenClass: 'job-card-chosen',
                dragClass: 'job-card-drag',
                onEnd: function (evt) {
                    const itemEl = evt.item;
                    const newStatus = evt.to.closest('.kanban-column').id;
                    const jobId = itemEl.getAttribute('data-id');
                    updateJobStatus(jobId, newStatus);
                }
            });
        })
        .catch(error => {
            console.error(`Error fetching ${status} jobs:`, error);
        });
}

// Function to create a job card element
function createJobCard(job) {
    let card = document.createElement('div');
    card.className = 'job-card';
    card.setAttribute('data-id', job.id);
    card.setAttribute('data-job-name', job.name || '');
    card.setAttribute('data-client-name', job.client ? job.client.name : '');
    card.setAttribute('data-job-description', job.description || '');
    card.setAttribute('data-job-number', job.job_number);
    card.innerHTML = `
        <h3><a href="/job/${job.id}/">Job ${job.job_number}: ${job.name}</a></h3>
        <p>${job.description}</p>
    `;
    return card;
}

// Function to update job status in the backend
function updateJobStatus(jobId, newStatus) {
    fetch(`/jobs/${jobId}/update_status/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ status: newStatus })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('Failed to update job status:', data.error);
        }
    })
    .catch(error => {
        console.error('Error updating job status:', error);
    });
}

// Function to filter jobs based on search input
function filterJobs() {
    const searchTerm = document.getElementById('search').value.toLowerCase();
    document.querySelectorAll('.job-card').forEach(card => {
        const jobName = card.dataset.jobName || '';
        const jobDescription = card.dataset.jobDescription || '';
        const client_name = card.dataset.client_name || '';
        const jobNumber = card.dataset.jobNumber || '';

        const combinedText = [jobName, jobDescription, client_name, jobNumber].join(' ').toLowerCase();

        // Log the combined text
        // console.log('Combined Text:', combinedText);

        // Check if the combined text contains the search term
        if (combinedText.includes(searchTerm)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

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
