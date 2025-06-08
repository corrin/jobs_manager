import { getCSRFToken } from "./job_file_handling.js";

function getJobIdFromUrl() {
  const match = window.location.pathname.match(/job\/(.+?)\//);
  return match ? match[1] : "";
}

function initImportQuote() {
  const button = document.getElementById("importQuoteButton");
  const fileInput = document.getElementById("importQuoteFile");
  if (!button || !fileInput) return;

  button.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    const jobId = getJobIdFromUrl();
    const formData = new FormData();
    formData.append("file", file);
    try {
      const resp = await fetch(`/api/jobs/${jobId}/import-quote/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCSRFToken() },
        body: formData,
      });
      const data = await resp.json();
      if (!resp.ok) {
        alert(data.error || "Import failed");
      } else {
        alert(`Imported ${data.partes_criadas} parts`);
        window.location.reload();
      }
    } catch (err) {
      console.error("Import failed", err);
      alert("Import failed");
    } finally {
      fileInput.value = "";
    }
  });
}

document.addEventListener("DOMContentLoaded", initImportQuote);
