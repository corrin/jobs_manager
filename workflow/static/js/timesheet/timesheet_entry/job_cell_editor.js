export class ActiveJobCellEditor {
    init(params) {
        this.value = params.value;
        this.params = params;
        this.jobs = window.timesheet_data.jobs; // Filtered to open jobs
        this.highlightedIndex = -1; // Track the highlighted job

        // Container
        this.div = document.createElement('div');
        this.div.className = 'dropdown position-relative';

        // Input
        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.className = 'form-control';
        this.input.placeholder = 'Search open jobs...';

        // Automatically focus input
        setTimeout(() => this.input.focus(), 0);

        // List container
        this.listDiv = document.createElement('div');
        this.listDiv.className = 'dropdown-menu p-3 w-100';
        this.listDiv.style.maxHeight = '200px';
        this.listDiv.style.overflowY = 'auto';
           
        // Populate initial list
        this.populateList(this.jobs);

        // Event listeners
        this.input.addEventListener('input', () => this.filterJobs());
        this.input.addEventListener('keydown', (e) => this.handleKeyDown(e));

        this.div.appendChild(this.input);
        this.div.appendChild(this.listDiv);
    }

    populateList(jobs) {
        this.listDiv.innerHTML = ''; // Clear previous results
        this.highlightedIndex = -1; // Reset highlight index

        if (jobs.length === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'dropdown-item text-muted';
            noResults.textContent = 'No jobs found';
            this.listDiv.appendChild(noResults);
            this.listDiv.classList.add('show'); // Ensure dropdown is shown even if empty
            return;
        }

        jobs.forEach((job, index) => {
            const jobRow = document.createElement('a');
            jobRow.className = 'dropdown-item';
            jobRow.href = '#';
            jobRow.textContent = job.job_display_name;
            jobRow.dataset.index = index;
            jobRow.onclick = (e) => {
                e.preventDefault();
                this.selectJob(job);
            };
            this.listDiv.appendChild(jobRow);
        });

        this.listDiv.classList.add('show'); // Ensure the dropdown is visible
    }

    filterJobs() {
        const searchTerm = this.input.value.trim().toLowerCase();
        const filteredJobs = this.jobs.filter(job =>
            job.job_display_name.toLowerCase().includes(searchTerm)
        );
        this.populateList(filteredJobs.slice(0, 10)); // Limit results to 10
    }

    handleKeyDown(event) {
        const items = this.listDiv.querySelectorAll('.dropdown-item');
        if (!items.length) return;

        switch (event.key) {
            case 'ArrowDown':
                this.highlightedIndex = Math.min(this.highlightedIndex + 1, items.length - 1);
                this.updateHighlight(items);
                break;

            case 'ArrowUp':
                this.highlightedIndex = Math.max(this.highlightedIndex - 1, 0);
                this.updateHighlight(items);
                break;

            case 'Enter':
                if (event.shiftKey) {
                    // Shift + Enter selects the highlighted job
                    if (this.highlightedIndex >= 0) {
                        items[this.highlightedIndex].click();
                    }
                }
                break;

            case 'Escape':
                this.params.stopEditing();
                break;

            default:
                break;
        }
    }

    updateHighlight(items) {
        items.forEach((item, index) => {
            item.classList.toggle('active', index === this.highlightedIndex);
        });

        const highlightedItem = items[this.highlightedIndex];
        if (highlightedItem) {
            highlightedItem.scrollIntoView({ block: 'nearest' });
        }
    }

    selectJob(job) {
        this.value = job.job_number;
        this.params.stopEditing();
    }

    getGui() {
        return this.div;
    }

    getValue() {
        return this.value;
    }

    destroy() {
        this.listDiv.classList.remove('show'); // Cleanup on destroy
    }

    isPopup() {
        return true;
    }
}
