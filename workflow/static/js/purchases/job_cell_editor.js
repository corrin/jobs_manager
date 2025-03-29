/**
 * Job Cell Editor for Purchase Orders
 *
 * Note: A similar version of this component exists at:
 * workflow/static/js/timesheet/timesheet_entry/job_cell_editor.js
 *
 * Make sure you update both files if you make any changes.
 *
 * Shared component for consistency across the application.
 */
export class ActiveJobCellEditor {
  init(params) {
    this.value = params.value;
    this.params = params;
    this.jobs = window.purchaseData.jobs; // Filtered to open jobs
    this.highlightedIndex = -1; // Track the highlighted job

    // Container
    this.div = document.createElement("div");
    this.div.className = "position-relative";

    // Input
    this.input = document.createElement("input");
    this.input.type = "text";
    this.input.className = "form-control";
    this.input.placeholder = "Search open jobs...";

    // Automatically focus input
    setTimeout(() => this.input.focus(), 0);

    // List container (dropdown)
    this.listDiv = document.createElement("div");
    this.listDiv.className = "dropdown-menu p-3 w-auto";
    this.listDiv.style.maxHeight = "200px";
    this.listDiv.style.overflowY = "auto";
    this.listDiv.style.zIndex = "1050"; // Ensure it appears above most elements
    this.listDiv.style.position = "absolute"; // Absolute positioning
    this.listDiv.style.display = "none"; // Initially hidden

    // Append the list to the body
    document.body.appendChild(this.listDiv);

    // Populate initial list
    this.populateList(this.jobs);

    // Event listeners
    this.input.addEventListener("input", () => this.filterJobs());
    this.input.addEventListener("keydown", (e) => this.handleKeyDown(e));
    this.input.addEventListener("focus", () => this.showDropdown());

    // Add mousedown listener to prevent blur when clicking dropdown
    this.listDiv.addEventListener("mousedown", (e) => {
      e.preventDefault();
      e.stopPropagation();
    });

    // Only hide dropdown on blur if not clicking inside listDiv
    this.input.addEventListener("blur", (e) => {
      setTimeout(() => {
        if (!this.listDiv.contains(document.activeElement)) {
          this.hideDropdown();
        }
      }, 200);
    });

    this.div.appendChild(this.input);
  }

  updateDropdownPosition() {
    const inputRect = this.input.getBoundingClientRect();
    this.listDiv.style.top = `${inputRect.bottom + window.scrollY}px`;
    this.listDiv.style.left = `${inputRect.left + window.scrollX}px`;
    this.listDiv.style.width = `${inputRect.width}px`;
  }

  showDropdown() {
    this.updateDropdownPosition();
    this.listDiv.style.display = "block";
    this.listDiv.classList.add("show");
  }

  hideDropdown() {
    this.listDiv.style.display = "none";
    this.listDiv.classList.remove("show");
  }

  populateList(jobs) {
    this.listDiv.innerHTML = "";
    this.highlightedIndex = -1;

    if (jobs.length === 0) {
      const noResults = document.createElement("div");
      noResults.className = "dropdown-item text-muted";
      noResults.textContent = "No jobs found";
      this.listDiv.appendChild(noResults);
      this.listDiv.classList.add("show");
      return;
    }

    jobs.forEach((job, index) => {
      const jobRow = document.createElement("a");
      jobRow.className = "dropdown-item";
      jobRow.href = "#";
      jobRow.textContent = job.job_display_name;
      jobRow.dataset.index = index;
      jobRow.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.selectJob(job);
      };
      this.listDiv.appendChild(jobRow);
    });

    this.listDiv.classList.add("show"); // Ensure the dropdown is visible
  }

  filterJobs() {
    const searchTerm = this.input.value.trim().toLowerCase();
    const filteredJobs = this.jobs.filter((job) =>
      job.job_display_name.toLowerCase().includes(searchTerm)
    );
    this.populateList(filteredJobs.slice(0, 10)); // Limit results to 10
  }

  handleKeyDown(event) {
    const items = this.listDiv.querySelectorAll(".dropdown-item");
    if (!items.length) return;

    switch (event.key) {
      case "ArrowDown":
        this.highlightedIndex = Math.min(
          this.highlightedIndex + 1,
          items.length - 1
        );
        this.updateHighlight(items);
        break;

      case "ArrowUp":
        this.highlightedIndex = Math.max(this.highlightedIndex - 1, 0);
        this.updateHighlight(items);
        break;

      case "Enter":
        if (event.shiftKey) {
          // Shift + Enter selects the highlighted job
          if (this.highlightedIndex >= 0) {
            items[this.highlightedIndex].click();
          }
        }
        break;

      case "Escape":
        this.params.stopEditing();
        break;

      default:
        break;
    }
  }

  updateHighlight(items) {
    items.forEach((item, index) => {
      item.classList.toggle("active", index === this.highlightedIndex);
    });

    const highlightedItem = items[this.highlightedIndex];
    if (highlightedItem) {
      highlightedItem.scrollIntoView({ block: "nearest" });
    }
  }

  selectJob(job) {
    this.value = job.id;
    this.params.stopEditing();
  }

  getGui() {
    return this.div;
  }

  getValue() {
    return this.value;
  }

  destroy() {
    if (this.listDiv.parentNode) {
      this.listDiv.parentNode.removeChild(this.listDiv);
    }
    this.listDiv.classList.remove("show");
  }

  isPopup() {
    return true;
  }
}