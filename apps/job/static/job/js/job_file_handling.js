import { renderMessages } from "/static/timesheet/js/timesheet_entry/messages.js"

function attachPrintCheckboxListeners() {
  document.querySelectorAll(".print-on-jobsheet").forEach((checkbox) => {
    checkbox.removeEventListener("change", handlePrintCheckboxChange);
    checkbox.addEventListener("change", handlePrintCheckboxChange);
  });
}

async function handlePrintCheckboxChange(e) {
  const fileId = e.target.dataset.fileId;
  const jobNumber = document.querySelector('[name="job_number"]').value;
  const printOnJobsheet = e.target.checked;
  await updatePrintOnJobsheet(fileId, jobNumber, printOnJobsheet);
}

export async function uploadJobFile(jobNumber, file, method) {
  if (!jobNumber || !file) return;

  if (file.name !== "JobSummary.pdf") showUploadFeedback(file.name);
  console.log(
    `[uploadJobFile] Starting file upload/update for job ${jobNumber} using ${method}`,
  );
  console.log(
    `[uploadJobFile] File details: name=${file.name}, size=${file.size}, type=${file.type}`,
  );

  const formData = createFileFormData(jobNumber, file);
  try {
    const response = await sendFileRequest(formData, method);
    processUploadResponse(response);
  } catch (error) {
    handleUploadError(error, method);
  }
}

function createFileFormData(jobNumber, file) {
  const formData = new FormData();
  formData.append("job_number", jobNumber);
  formData.append("files", file);
  return formData;
}

async function sendFileRequest(formData, method) {
  const endpoint = "/api/job-files/";
  console.log(
    `[uploadJobFile] Sending request to ${endpoint} (method=${method})`,
  );

  return fetch(endpoint, {
    method: method,
    headers: {
      "X-CSRFToken": getCSRFToken(),
    },
    body: formData,
  });
}

export function getCSRFToken() {
  return document.querySelector('[name="csrfmiddlewaretoken"]').value;
}

async function processUploadResponse(response) {
  const data = await response.json();
  console.log(
    `[uploadJobFile] Response: status=${response.status}, ok=${response.ok}`,
    data,
  );

  hideUploadFeedback();

  if (response.ok) {
    updateFileList(data.uploaded);
  } else {
    console.error(`[uploadJobFile] Failed to upload/update file.`, data);
  }
}

function handleUploadError(error, method) {
  hideUploadFeedback();
  console.error(`[uploadJobFile] Error during ${method} request:`, error);
}

export async function deleteFile(fileId) {
  if (!fileId) return;

  console.log(`[deleteFile] Deleting file with ID=${fileId}`);
  if (!confirm("Are you sure you want to delete this file?")) return;

  try {
    const response = await fetch(`/api/job-files/${fileId}`, {
      method: "DELETE",
      headers: {
        "X-CSRFToken": getCSRFToken(),
      },
    });

    handleDeleteResponse(response, fileId);
  } catch (error) {
    console.error("[deleteFile] Error deleting file:", error);
  }
}

function handleDeleteResponse(response, fileId) {
  if (!response.ok) {
    console.error(
      `[deleteFile] Failed to delete file ID=${fileId}. Response status: ${response.status}`,
    );
    return;
  }

  console.log(`[deleteFile] File with ID=${fileId} deleted successfully`);
  removeFileCard(fileId);
}

function removeFileCard(fileId) {
  const fileCard = document
    .querySelector(`[data-file-id="${fileId}"]`)
    ?.closest(".file-card");
  if (fileCard) {
    fileCard.remove();
    updateNoFilesMessage();
  }
}

export async function checkExistingJobFile(jobNumber, fileName) {
  console.log(
    `[checkExistingJobFile] Checking if fileName="${fileName}" exists for job ${jobNumber}`,
  );

  try {
    const response = await fetch(`/api/job-files/${jobNumber}`);
    if (!response.ok) return false;

    const files = await response.json();
    return files.some((file) => file.filename === fileName);
  } catch (error) {
    console.error("Error checking existing job file:", error);
    return false;
  }
}

export async function updatePrintOnJobsheet(
  fileId,
  jobNumber,
  printOnJobsheet,
) {
  console.log(
    `[updatePrintOnJobsheet] Starting update for fileId=${fileId}, jobNumber=${jobNumber}, printOnJobsheet=${printOnJobsheet}`,
  );
  try {
    const response = await fetch(`/api/job-files/${jobNumber}`);

    if (!response.ok) {
      console.log(
        `[updatePrintOnJobsheet] Failed to fetch file data. Response status: ${response.status}`,
      );
      return;
    }

    const files = await response.json();
    const fileData = files.find((file) => file.id === fileId);

    if (!fileData) {
      console.log(`[updatePrintOnJobsheet] No file found with ID=${fileId}`);
      return;
    }

    console.log(`[updatePrintOnJobsheet] Found file data:`, fileData);

    const formData = new FormData();
    formData.append("job_number", jobNumber);
    formData.append("filename", fileData.filename);
    formData.append("print_on_jobsheet", printOnJobsheet ? "true" : "false");

    console.log(
      `[updatePrintOnJobsheet] Sending update request with formData:`,
      {
        filename: fileData.filename,
        printOnJobsheet: printOnJobsheet,
      },
    );

    const updateResponse = await fetch(`/api/job-files/`, {
      method: "PUT",
      headers: {
        "X-CSRFToken": document.querySelector('[name="csrfmiddlewaretoken"]')
          .value,
      },
      body: formData,
    });

    if (updateResponse.ok) {
      const data = await updateResponse.json();
      console.log(`[updatePrintOnJobsheet] Update successful:`, data);
      attachPrintCheckboxListeners();
    } else {
      console.log(
        `[updatePrintOnJobsheet] Update failed. Response status: ${updateResponse.status}`,
      );
    }
  } catch (error) {
    console.error("[updatePrintOnJobsheet] Error updating job file:", error);
  }
}

function updateFileList(newFiles) {
  if (!newFiles || newFiles.length === 0) return;

  const grid = document.querySelector(".job-files-grid") || createNewFileGrid();

  newFiles.forEach((file) => {
    // Ignore summary in visual list
    if (file.filename === "JobSummary.pdf") return;

    const card = document.createElement("div");
    card.className = "file-card";
    card.dataset.fileId = file.id;

    card.innerHTML = `
            <div class="thumbnail-container no-thumb">
                <span class="file-extension">${getFileExtension(file.filename)}</span>
            </div>
            <div class="file-info">
                <a href="/api/job-files/${file.file_path}" target="_blank">${file.filename}</a>
                <span class="timestamp">(Just uploaded)</span>
            </div>
            <div class="file-controls">
                <label class="print-checkbox">
                    <input type="checkbox" name="jobfile_${file.id}_print_on_jobsheet"
                        class="print-on-jobsheet"
                        data-file-id="${file.id}"
                        ${file.print_on_jobsheet ? "checked" : ""}>
                    Print on Job Sheet
                </label>
                <button class="btn btn-sm btn-danger delete-file" data-file-id="${file.id}">
                    Delete
                </button>
            </div>
        `;

    grid.appendChild(card);
  });

  attachPrintCheckboxListeners();
  updateNoFilesMessage();
}

function createNewFileGrid() {
  const fileList = document.querySelector("#file-list");

  // Remove any existing messages
  const noFilesMsg = fileList.querySelector("p");
  if (noFilesMsg) noFilesMsg.remove();

  const grid = document.createElement("div");
  grid.className = "job-files-grid";
  fileList.appendChild(grid);

  updateNoFilesMessage();
  return grid;
}

// Get file extension to display in the file card
function getFileExtension(filename) {
  const parts = filename.split(".");
  return parts.length > 1 ? `.${parts.pop().toUpperCase()}` : filename;
}

function showUploadFeedback(filename) {
  const feedbackEl = getOrCreateFeedbackElement();
  updateFeedbackFilename(feedbackEl, filename);
  feedbackEl.style.display = "flex";
}

function getOrCreateFeedbackElement() {
  let feedbackEl = document.getElementById("file-upload-feedback");

  if (feedbackEl) return feedbackEl;

  feedbackEl = createFeedbackElement();
  ensureFeedbackStyles();
  document.body.appendChild(feedbackEl);

  return feedbackEl;
}

function createFeedbackElement() {
  const element = document.createElement("div");
  element.id = "file-upload-feedback";
  element.className = "upload-feedback";

  element.innerHTML = `
    <div class="upload-spinner">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>
    <div>Uploading file</div>
    <div class="upload-filename"></div>
  `;

  return element;
}

function ensureFeedbackStyles() {
  if (document.getElementById("upload-feedback-styles")) return;

  const style = document.createElement("style");
  style.id = "upload-feedback-styles";
  style.textContent = `
    .upload-feedback {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(255, 255, 255, 0.9);
      border-radius: 5px;
      padding: 20px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
      z-index: 9999;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .upload-spinner {
      margin-bottom: 15px;
    }
    .upload-filename {
      font-weight: bold;
      max-width: 250px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  `;
  document.head.appendChild(style);
}

function updateFeedbackFilename(feedbackEl, filename) {
  feedbackEl.querySelector(".upload-filename").textContent = filename;
}

function hideUploadFeedback() {
  const feedbackEl = document.getElementById("file-upload-feedback");
  if (feedbackEl) {
    feedbackEl.style.display = "none";
  }
}

// Verify the existence of real files (excluding JobSummary.pdf)
function updateNoFilesMessage() {
  const grid = document.querySelector(".job-files-grid");
  const fileList = document.querySelector("#file-list");

  if (!fileList) return;

  const hasVisibleFiles = grid && grid.querySelector(".file-card:not(.d-none)");
  const existingMessage = fileList.querySelector(".alert.alert-info");

  if (hasVisibleFiles) {
    if (existingMessage) existingMessage.remove();
    return;
  }

  // No visible files case
  if (existingMessage) return; // Message already exists

  // Clean up empty grid
  if (grid && grid.children.length === 0) {
    grid.remove();
  }

  // Create and add the message
  const noFilesMsg = createNoFilesMessage();
  fileList.appendChild(noFilesMsg);
}

function createNoFilesMessage() {
  const message = document.createElement("div");
  message.className = "alert alert-info";
  message.innerHTML =
    '<i class="bi bi-info-circle me-2"></i>No files attached to this job.';
  return message;
}

document.addEventListener("DOMContentLoaded", function () {
  attachPrintCheckboxListeners();
  updateNoFilesMessage();
  setupFileUploadEvents();
  setupDocumentEvents();
});

function setupFileUploadEvents() {
  const fileInput = document.getElementById("file-input");
  if (fileInput) {
    fileInput.addEventListener("change", handleFileInputChange);
  }

  const dropZone = document.querySelector(".file-drop-zone");
  if (dropZone) {
    setupDropZoneEvents(dropZone);
  }

  const captureButton = document.getElementById("capture-photo");
  if (captureButton) {
    captureButton.addEventListener("click", handlePhotoCapture);
  }
}

async function handlePhotoCapture(e) {
  e.preventDefault();

  const jobNumber = document.querySelector('[name="job_number"]').value;
  if (!jobNumber) {
    renderMessages([
      { level: "danger", message: "A job number is required to add photos." },
    ]);
    return;
  }

  try {
    const photoFile = await capturePhotoFromCamera(jobNumber);

    await processFiles([photoFile], jobNumber);
  } catch (error) {
    if (error.message !== "Photo capture canceled") {
      console.error("[handlePhotocapture] Error capturing photo:", error);
    }
  }
}

function setupDropZoneEvents(dropZone) {
  dropZone.addEventListener("drop", handleFileDrop);

  ["dragenter", "dragover"].forEach((event) =>
    dropZone.addEventListener(
      event,
      (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add("drag-over");
      },
      false,
    ),
  );

  ["dragleave", "drop"].forEach((event) =>
    dropZone.addEventListener(
      event,
      (e) => {
        if (event === 'dragleave') {
          e.preventDefault();
        }
        dropZone.classList.remove("drag-over");
      },
      false,
    ),
  );
}

async function handleFileInputChange(event) {
  const files = event.target.files;
  if (!files.length) return;

  const jobNumber = document.querySelector('[name="job_number"]').value;
  await processFiles(files, jobNumber);
}

async function handleFileDrop(e) {
  e.preventDefault();
  e.stopPropagation();
  const files = e.dataTransfer.files;
  if (!files.length) return;

  const jobNumber = document.querySelector('[name="job_number"]').value;
  await processFiles(files, jobNumber);
}

async function processFiles(files, jobNumber) {
  for (const file of files) {
    if (file.size === 0) {
      alert(`Cannot upload 0-byte file: ${file.name}`);
      continue;
    }

    try {
      let fileToUpload = file;

      if (isImageFile(file)) {
        console.log(
          `[processFiles] Compressing image before upload: ${file.name}`,
        );
        fileToUpload = await compressImage(file);
      }

      const fileExists = await checkExistingJobFile(
        jobNumber,
        fileToUpload.name,
      );
      await uploadJobFile(jobNumber, fileToUpload, fileExists ? "PUT" : "POST");
    } catch (error) {
      console.error(
        `[processFiles] Error while searching file ${file.name}:`,
        error,
      );
    }
  }
}

function setupDocumentEvents() {
  document.addEventListener("click", function (e) {
    if (e.target.classList.contains("delete-file")) {
      const fileId = e.target.dataset.fileId;
      if (fileId) deleteFile(fileId);
    }
  });
}

function isImageFile(file) {
  return file.type.startsWith("image/");
}

async function compressImage(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);

    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target.result;

      img.onload = () => {
        const maxWidth = 1280;
        const maxHeight = 960;

        let width = img.width;
        let height = img.height;

        if (width > maxWidth || height > maxHeight) {
          const scaleWidth = maxWidth / width;
          const scaleHeight = maxHeight / height;
          const scaleFactor = Math.min(scaleWidth, scaleHeight);

          width = Math.floor(width * scaleFactor);
          height = Math.floor(height * scaleFactor);
        }

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, width, height);
        canvas.toBlob(
          (blob) => {
            const compressedFile = new File([blob], file.name, {
              type: "image/jpeg",
              lastModified: Date.now(),
            });

            console.log(`[compressImage] Compressed image ${file.name}:
            Original: ${(file.size / 1024 / 1024).toFixed(2)}MB,
            Compressed: ${(compressedFile.size / 1024 / 1024).toFixed(2)}MB
          `);

            resolve(compressedFile);
          },
          "image/jpeg",
          0.7,
        );
      };
    };
  });
}

async function capturePhotoFromCamera(jobNumber) {
  return new Promise((resolve, reject) => {
    try {
      const modalHtml = `
        <div class="modal fade" id="cameraModal" tabindex="-1" aria-labelledby="cameraModalLabel" aria-hidden="true">
          <div class="modal-dialog modal-lg modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="cameraModalLabel">Photo Capture</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>
              <div class="modal-body p-0 bg-dark">
                <video id="camera-preview" class="w-100" autoplay playsinline></video>
                <canvas id="camera-canvas" class="d-none"></canvas>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel Capture</button>
                <button type="button" class="btn btn-primary" id="capture-button">
                  <i class="bi bi-camera"></i> Capture Photo
                </button>
              </div>
            </div>
          </div>
        </div>
      `;

      document.body.insertAdjacentHTML("beforeend", modalHtml);

      const cameraModal = document.getElementById("cameraModal");
      const videoElement = document.getElementById("camera-preview");
      const captureButton = document.getElementById("capture-button");
      const canvas = document.getElementById("camera-canvas");

      const modalInstance = new bootstrap.Modal(cameraModal);

      modalInstance.show();

      const cleanup = () => {
        if (videoElement.srcObject) {
          videoElement.srcObject.getTracks().forEach((track) => track.stop());
        }

        modalInstance.hide();

        cameraModal.addEventListener("hidden.bs.modal", () => {
          cameraModal.remove();
        });
      };

      cameraModal.addEventListener("hidden.bs.modal", () => {
        cleanup();
        reject(new Error("Photo capture canceled"));
      });

      navigator.mediaDevices
        .getUserMedia({
          video: {
            facingMode: "environment",
            width: { ideal: 1280 },
            height: { ideal: 960 },
          },
        })
        .then((stream) => {
          videoElement.srcObject = stream;

          captureButton.addEventListener("click", () => {
            canvas.width = videoElement.videoWidth;
            canvas.height = videoElement.videoHeight;

            const context = canvas.getContext("2d");
            context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

            canvas.toBlob(
              (blob) => {
                const timestamp = new Date()
                  .toISOString()
                  .replace(/[:.]/g, "-");
                const file = new File([blob], `photo-${timestamp}.jpg`, {
                  type: "image/jpeg",
                });

                cleanup();

                resolve(file);
              },
              "image/jpeg",
              0.85,
            );
          });
        })
        .catch((error) => {
          console.error("Error trying to access camera:", error);
          cleanup();
          renderMessages([
            {
              level: "danger",
              message:
                "It wasn't possible to access the camera. Check if you granted permission.",
            },
          ]);
          reject(error);
        });
    } catch (error) {
      console.error("Error trying to access camera:", error);
      renderMessages([
        {
          level: "danger",
          message: "Error initializing camera " + error.message,
        },
      ]);
      reject(error);
    }
  });
}
