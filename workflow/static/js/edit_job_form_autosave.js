import { createNewRow } from '/static/js/deseralise_job_pricing.js';

let dropboxToken = null;

// Debounce function to avoid frequent autosave calls
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Function to collect all data from the form
function collectAllData() {
    const data = {};  // Collects main form data

    // Collect data directly from visible input fields in the form
    const formElements = document.querySelectorAll('.autosave-input');

    formElements.forEach(element => {
        let value;
        if (element.type === 'checkbox') {
            value = element.checked;
        } else {
            value = element.value.trim() === "" ? null : element.value;
        }
        data[element.name] = value;
    });

    // Add job validity check
    data.job_is_valid = checkJobValidity();

    // 2. Get all historical pricings that were passed in the initial context
    let historicalPricings = JSON.parse(JSON.stringify(window.historical_job_pricings_json));

    // 3. Collect latest revisions from AG Grid
    data.latest_estimate_pricing = collectGridData('estimate');
    data.latest_quote_pricing = collectGridData('quote');
    data.latest_reality_pricing = collectGridData('reality');

    // 4. Add the historical pricings to jobData
    data.historical_pricings = historicalPricings;

    return data;

}

function checkJobValidity() {
    // Check if all required fields are populated
    const requiredFields = ['job_name', 'client_id', 'contact_person', 'job_number'];
    const isValid = requiredFields.every(field => {
        const value = document.getElementById(field)?.value;
        return value !== null && value !== undefined && value.trim() !== '';
    });

    return isValid;
}

function isNonDefaultRow(data, gridName) {
    const defaultRow = createNewRow(gridName);

    // Compare data to the default row
    for (const key in defaultRow) {
        if (defaultRow[key] !== data[key]) {
            return true; // Not a default row
        }
    }

    return false; // Matches default row, so it's invalid
}

function collectGridData(section) {
    const grids = ['TimeTable', 'MaterialsTable', 'AdjustmentsTable'];
    const sectionData = {};

    grids.forEach(gridName => {
        const gridKey = `${section}${gridName}`;
        const gridData = window.grids[gridKey];

        if (gridData && gridData.api) {
            const rowData = [];
            gridData.api.forEachNode(node => {
                if (isNonDefaultRow(node.data, gridName)) {
                    rowData.push(node.data);
                }
            });

            // Convert to the correct key name
            let entryKey = gridName.toLowerCase().replace('table', '')
            if (entryKey === 'time') entryKey = 'time';
            if (entryKey === 'materials') entryKey = 'material';
            if (entryKey === 'adjustments') entryKey = 'adjustment';
            entryKey += '_entries';

            sectionData[entryKey] = rowData;
        } else {
            console.error(`Grid or API not found for ${gridKey}`);
        }
    });

    return sectionData;
}

async function getDropboxToken() {
    if (!dropboxToken) {
        const response = await fetch('/api/get-env-variable/?var_name=DROPBOX_ACCESS_TOKEN');
        if (response.ok) {
            const data = await response.json();
            dropboxToken = data.value; // Cache the token
            console.log('Fetched and cached Dropbox token:', dropboxToken);
        } else {
            console.error('Failed to fetch Dropbox token');
        }
    }
    return dropboxToken;
}

async function uploadToDropbox(file, dropboxPath) {
    const accessToken = await getDropboxToken();
    if (!accessToken) {
        console.error("No Dropbox token available");
        return false;
    }

    try {
        const response = await fetch("https://content.dropboxapi.com/2/files/upload", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${accessToken}`,
                "Dropbox-API-Arg": JSON.stringify({
                    path: dropboxPath,
                    mode: "overwrite",
                    autorename: false,
                    mute: false,
                }),
                "Content-Type": "application/octet-stream",
            },
            body: file,
        });

        if (!response.ok) {
            // Check Content-Type to handle non-JSON errors
            const contentType = response.headers.get("Content-Type");
            if (contentType && contentType.includes("application/json")) {
                const errorData = await response.json();
                console.error("Dropbox API error:", errorData);
            } else {
                const errorText = await response.text(); // Handle non-JSON responses
                console.error("Dropbox upload failed (non-JSON):", errorText);
            }
            return false;
        }

        // Parse and log the successful response
        const data = await response.json();
        console.log("File uploaded to Dropbox:", data);
        return true;
    } catch (error) {
        console.error("Dropbox upload failed:", error);
        return false;
    }
}

function addGridToPDF(doc, title, rowData, startY) {
    // Extract column headers from the first row's keys
    const columns = Object.keys(rowData[0] || {});
    const rows = rowData.map((row) => columns.map((col) => row[col] || ""));

    // Add table to the PDF
    doc.text(title, 10, startY);
    doc.autoTable({
        head: [columns],
        body: rows,
        startY: startY + 10,
    });

    // Return the new Y position after the table
    return doc.lastAutoTable.finalY + 10;
}

async function generateAndUploadPDF(jobData) {
    const { jsPDF } = window.jspdf; // Access jsPDF globally
    const doc = new jsPDF();

    try {
        // Add job details
        doc.setFontSize(16);
        doc.text(`Job Details: ${jobData.job_name}`, 10, 10);
        doc.setFontSize(12);
        doc.text(`Client: ${jobData.client_name}`, 10, 20);

        // Add grids using collected data
        const grids = [
            { title: "Time Entries", data: jobData.latest_estimate_pricing.time_entries },
            { title: "Material Entries", data: jobData.latest_estimate_pricing.material_entries },
            { title: "Adjustment Entries", data: jobData.latest_estimate_pricing.adjustment_entries },
        ];

        let startY = 30; // Initial Y position
        grids.forEach((grid) => {
            if (grid.data && grid.data.length) {
                startY = addGridToPDF(doc, grid.title, grid.data, startY);
            }
        });

        // Convert the PDF to a Blob
        const pdfBlob = new Blob([doc.output("blob")], { type: "application/pdf" });

        // Upload the PDF to Dropbox
        const dropboxPath = `/MSM Workflow/Job-${jobData.job_number}/JobSummary.pdf`;
        const success = await uploadToDropbox(pdfBlob, dropboxPath);
        if (success) {
            console.log(`PDF for Job ${jobData.job_number} successfully uploaded to Dropbox`);
        } else {
            console.error(`PDF upload for Job ${jobData.job_number} failed`);
        }
    } catch (error) {
        console.error("Error generating and uploading PDF:", error);
    }
}

// Autosave function to send data to the server
function autosaveData() {
    const collectedData = collectAllData();
    if (Object.keys(collectedData).length === 0) {
        console.error("No data collected for autosave.");
        return;
    }
    saveDataToServer(collectedData);
}

// Function to make POST request to the API endpoint
function saveDataToServer(collectedData) {
    console.log('Autosaving data to /api/autosave-job/...', collectedData);

    fetch('/api/autosave-job/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(collectedData)
    })
    .then(response => {
        if (!response.ok) {
            // If the server response is not OK, it might contain validation errors.
            return response.json().then(data => {
                if (data.errors) {
                    handleValidationErrors(data.errors);
                }
                throw new Error('Validation errors occurred');
            });
        }
        return response.json();
    })
    .then(data => {
        generateAndUploadPDF(collectedData);
        console.log('Autosave successful:', data);
    })
    .catch(error => {
        console.error('Autosave failed:', error);
    });
}

function handleValidationErrors(errors) {
    // Clear previous error messages
    document.querySelectorAll('.invalid-feedback').forEach(errorMsg => errorMsg.remove());
    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

    // Display new errors
    for (const [field, messages] of Object.entries(errors)) {
        const element = document.querySelector(`[name="${field}"]`);
        if (element) {
            element.classList.add('is-invalid');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            errorDiv.innerText = messages.join(', ');
            element.parentElement.appendChild(errorDiv);

            // Attach listener to remove the error once the user modifies the field
            element.addEventListener('input', () => {
                element.classList.remove('is-invalid');
                if (element.nextElementSibling && element.nextElementSibling.classList.contains('invalid-feedback')) {
                    element.nextElementSibling.remove();
                }
            }, { once: true });
        }
    }
}

// Helper function to get CSRF token for Django
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function removeValidationError(element) {
    element.classList.remove('is-invalid');
    if (element.nextElementSibling && element.nextElementSibling.classList.contains('invalid-feedback')) {
        element.nextElementSibling.remove();
    }
}

// Debounced version of the autosave function
const debouncedAutosave = debounce(function() {
    console.log("Debounced autosave called");
    autosaveData();
}, 1000);

const debouncedRemoveValidation = debounce(function(element) {
    console.log("Debounced validation removal called for element:", element);
    removeValidationError(element);
}, 1000);

// Attach autosave to form elements (input, select, textarea)
// Synchronize visible UI fields with hidden form fields
document.addEventListener('DOMContentLoaded', function () {
    // Synchronize all elements with the 'autosave-input' class
    const autosaveInputs = document.querySelectorAll('.autosave-input');

    // Attach change event listener to handle special input types like checkboxes
    autosaveInputs.forEach(fieldElement => {
        fieldElement.addEventListener('blur', function() {
            console.log("Blur event fired for:", fieldElement);
            debouncedRemoveValidation(fieldElement);
            debouncedAutosave();
        });

        if (fieldElement.type === 'checkbox') {
            fieldElement.addEventListener('change', function() {
                console.log("Change event fired for checkbox:", fieldElement);
                debouncedRemoveValidation(fieldElement);
                debouncedAutosave();
            });
        }

        if (fieldElement.tagName === 'SELECT') {
            fieldElement.addEventListener('change', function() {
                console.log("Change event fired for select:", fieldElement);
                debouncedRemoveValidation(fieldElement);
                debouncedAutosave();
            });
        }
    });

    // Function to validate all required fields before autosave
    // Unused?
    // function validateAllFields() {
    //     let allValid = true;
    //
    //     autosaveInputs.forEach(input => {
    //         if (input.hasAttribute('required') && input.type !== "checkbox" && input.value.trim() === '') {
    //             // Add validation error for required fields that are empty
    //             addValidationError(input, 'This field is required.');
    //             allValid = false;
    //         } else if (input.type === "checkbox" && input.hasAttribute('required') && !input.checked) {
    //             // If a checkbox is required but not checked
    //             addValidationError(input, 'This checkbox is required.');
    //             allValid = false;
    //         } else {
    //             // Remove validation error if field is valid
    //             removeValidationError(input);
    //         }
    //     });
    //
    //     return allValid;
    // }

    // // Function to add validation error to an input
    // Unused?
    // function addValidationError(element, message) {
    //     element.classList.add('is-invalid');
    //     if (!element.nextElementSibling || !element.nextElementSibling.classList.contains('invalid-feedback')) {
    //         const errorDiv = document.createElement('div');
    //         errorDiv.className = 'invalid-feedback';
    //         errorDiv.innerText = message;
    //         element.parentElement.appendChild(errorDiv);
    //     }
    // }

    // Function to remove validation error from an input
    // Unused?



});
