import { createNewRow } from "./deserialize_job_pricing.js";
import {
  capitalize,
  calculateTotalRevenue,
  calculateTotalCost,
  checkRealityValues,
} from "./grid/grid_utils.js";
import { uploadJobFile, checkExistingJobFile } from "./job_file_handling.js";
import { calculateSimpleTotals } from "./grid/revenue_cost_options.js";
import { renderMessages } from "/static/timesheet/js/timesheet_entry/messages.js";
import { debugLog } from "../env.js";
import { initHistoricalNavigation } from "./historical_pricing_navigation.js";

// Debounce function to avoid frequent autosave calls
function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

// Function to collect all data from the form
export function collectAllData() {
  const data = {}; // Collects main form data

  // Collect data directly from visible input fields in the form
  const formElements = document.querySelectorAll(".autosave-input");

  formElements.forEach((element) => {
    let value;
    if (element.type === "checkbox") {
      value = element.checked;
      if (element.classList.contains("print-on-jobsheet")) {
        const fileId = element.name.match(
          /jobfile_([a-f0-9-]+)_print_on_jobsheet/,
        )[1];
        if (!data.job_files) {
          data.job_files = {};
        }
        data.job_files[fileId] = { print_on_jobsheet: value };
        return; // Skip adding this checkbox to the main data object
      }
    } else {
      value = element.value.trim() === "" ? null : element.value;
    }

    if (element.name === "client_id" && !value) {
      console.error(
        "Client ID missing. Ensure client selection updates the hidden input.",
      );
    }
    data[element.name] = value;
  });

  // Collect additional fields not present in form inputs
  const additionalFields = {
    client_name:
      document.getElementById("job-client-name")?.textContent || "N/A",
    created_at: document.getElementById("job-created-at")?.textContent || "N/A",
  };
  Object.assign(data, additionalFields);

  // 2. Get all historical pricings that were passed in the initial context
  let historicalPricings = JSON.parse(
    JSON.stringify(window.historical_job_pricings_json),
  );

  // 3. Collect latest revisions from AG Grid
  data.latest_estimate_pricing = collectGridData("estimate");
  data.latest_quote_pricing = collectGridData("quote");
  data.latest_reality_pricing = collectGridData("reality");

  // 4. Add the historical pricings to jobData
  data.historical_pricings = historicalPricings;

  // console.log('Collected Data:', data);
  data.job_is_valid = checkJobValidity(data);

  return data;
}

function checkJobValidity(data) {
  console.log("Checking job validity...");

  const requiredFields = ["name", "client_xero_id", "job_number"];
  const invalidFields = requiredFields.filter(
    (field) => !data[field] || data[field].trim() === "" || data[field] == null,
  );

  document
    .querySelectorAll(".is-invalid")
    .forEach((el) => el.classList.remove("is-invalid"));

  if (invalidFields.length > 0) {
    console.warn(`Invalid fields: ${invalidFields.join(", ")}`);

    let firstInvalidElement = null;

    invalidFields.forEach((field) => {
      const element = document.querySelector(`[name='${field}']`);
      if (element) {
        element.classList.add("is-invalid");
        if (!firstInvalidElement) {
          firstInvalidElement = element;
        }
      }
    });

    renderMessages(
      [
        {
          level: "error",
          message:
            "⚠️ You must complete all required fields before proceeding.",
        },
      ],
      "job-details",
    );
    return false;
  } else {
    return true;
  }
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
  console.log(`collectGridData called for section: ${section}`);
  // Ensuring reality section is always complex
  const isComplex =
    section === "reality" ||
    document.getElementById("complex-job").textContent.toLowerCase() === "true";
  console.log(
    `Job complexity status for section ${section}: isComplex=${isComplex}`,
  );

  switch (isComplex) {
    case true:
      console.log(`Using advanced grid collection for ${section}`);
      const advancedData = collectAdvancedGridData(section);
      console.log(`Advanced grid data collected for ${section}:`, advancedData);
      return advancedData;
    case false:
      console.log(`Using simple grid collection for ${section}`);
      const simpleData = collectSimpleGridData(section);
      console.log(`Simple grid data collected for ${section}:`, simpleData);
      return simpleData;
    default:
      console.error(
        `Unknown grid state: "${isComplex}" for section ${section}`,
      );
      return {};
  }
}

function collectAdvancedGridData(section) {
  const grids =
    section === "reality"
      ? ["MaterialsTable", "AdjustmentsTable"]
      : ["TimeTable", "MaterialsTable", "AdjustmentsTable"];
  const sectionData = {};

  debugLog(`collectAdvancedGridData starting for section: ${section}`);

  grids.forEach((gridName) => {
    const gridKey = `${section}${gridName}`;
    const gridData = window.grids[gridKey];
    debugLog(
      `Processing grid ${gridKey}, exists: ${!!gridData}, has API: ${!!(gridData && gridData.api)}`,
    );

    if (gridData && gridData.api) {
      const rowData = [];
      let rowCount = 0;

      gridData.api.forEachNode((node) => {
        rowCount++;
        const isValid = isNonDefaultRow(node.data, gridName);
        debugLog(
          `Grid ${gridKey}: Row ${rowCount} validation: ${isValid}`,
          node.data,
        );

        if (isValid) {
          const data = { ...node.data };
          data.minutes_per_item = data.mins_per_item;
          delete data.mins_per_item;
          rowData.push(data);
          debugLog(`Added row to ${gridKey} data:`, data);
        } else {
          debugLog(`Skipping default row in ${gridKey}:`, node.data);
        }
      });

      // Convert to the correct key name
      let entryKey = gridName.toLowerCase().replace("table", "");
      if (entryKey === "time") entryKey = "time";
      if (entryKey === "materials") entryKey = "material";
      if (entryKey === "adjustments") entryKey = "adjustment";
      entryKey += "_entries";

      sectionData[entryKey] = rowData;
      debugLog(
        `Added ${rowData.length} rows to ${section}.${entryKey} out of ${rowCount} total rows`,
      );
    } else {
      console.error(`Grid or API not found for ${gridKey}`);
    }
  });

  // To ensure that reality section always has an empty time entries array to avoid autosaving
  if (section === "reality") {
    sectionData["time_entries"] = [];
  }

  debugLog(`collectAdvancedGridData completed for ${section}:`, sectionData);
  return sectionData;
}

export function collectSimpleGridData(section) {
  debugLog(`collectSimpleGridData starting for section: ${section}`);
  const sectionData = {};

  // ===================== 1) TIME  =====================
  {
    const timeKey = `simple${capitalize(section)}TimeTable`;
    const timeGrid = window.grids[timeKey];
    debugLog(
      `Processing simple time grid ${timeKey}, exists: ${!!timeGrid}, has API: ${!!(timeGrid && timeGrid.api)}`,
    );

    let timeEntries = [];
    const seenTimeEntries = new Set();

    if (timeGrid && timeGrid.api) {
      let rowCount = 0;
      timeGrid.api.forEachNode((node) => {
        rowCount++;
        const row = node.data || {};
        const description = row.description?.trim() || "";
        const hours = parseFloat(row.hours) || 0;
        const wage = parseFloat(row.wage_rate) || 0;
        const charge = parseFloat(row.charge_out_rate) || 0;
        const costTime = parseFloat(row.cost_of_time) || 0;
        const valueTime = parseFloat(row.value_of_time) || 0;

        const isEmptyRow = hours === 0;

        // Create unique key for time entry
        const entryKey = `${description}-${hours}-${wage}-${charge}`;
        debugLog(
          `Time row ${rowCount}: "${description}", hours=${hours}, empty=${isEmptyRow}, duplicate=${seenTimeEntries.has(entryKey)}`,
        );

        if (!isEmptyRow && !seenTimeEntries.has(entryKey)) {
          const totalMinutes = hours * 60;
          const entry = {
            description: description,
            items: 1,
            minutes_per_item: totalMinutes,
            total_minutes: totalMinutes,
            wage_rate: wage,
            charge_out_rate: charge,
            cost: costTime,
            revenue: valueTime,
          };
          timeEntries.push(entry);
          seenTimeEntries.add(entryKey);
          debugLog(`Added time entry:`, entry);
        } else if (isEmptyRow) {
          debugLog(`Skipping empty time row: ${description}, hours=${hours}`);
        } else {
          debugLog(`Skipping duplicate time entry: ${entryKey}`);
        }
      });
      debugLog(
        `Processed ${rowCount} rows in time grid, added ${timeEntries.length} entries`,
      );
    } else {
      debugLog(`Time grid ${timeKey} not found or missing API`);
    }
    sectionData.time_entries = timeEntries;
  }

  // ===================== 2) MATERIALS =====================
  {
    const matKey = `simple${capitalize(section)}MaterialsTable`;
    const matGrid = window.grids[matKey];
    debugLog(
      `Processing simple materials grid ${matKey}, exists: ${!!matGrid}, has API: ${!!(matGrid && matGrid.api)}`,
    );

    let materialEntries = [];
    const seenMaterialEntries = new Set();

    if (matGrid && matGrid.api) {
      let rowCount = 0;
      matGrid.api.forEachNode((node) => {
        rowCount++;
        const row = node.data || {};
        const description = row.description?.trim() || "";
        const materialCost = parseFloat(row.material_cost) || 0;
        const retailPrice = parseFloat(row.retail_price) || 0;

        const isEmptyRow = materialCost === 0 && retailPrice === 0;

        // Create unique key for material entry
        const entryKey = `${description}-${materialCost}-${retailPrice}`;
        debugLog(
          `Material row ${rowCount}: "${description}", cost=${materialCost}, retail=${retailPrice}, empty=${isEmptyRow}, duplicate=${seenMaterialEntries.has(entryKey)}`,
        );

        if (!isEmptyRow && !seenMaterialEntries.has(entryKey)) {
          const entry = {
            description: description,
            quantity: 1,
            unit_cost: materialCost,
            unit_revenue: retailPrice,
            revenue: retailPrice,
          };
          materialEntries.push(entry);
          seenMaterialEntries.add(entryKey);
          debugLog(`Added material entry:`, entry);
        } else if (isEmptyRow) {
          debugLog(`Skipping empty material row: ${description}`);
        } else {
          debugLog(`Skipping duplicate material entry: ${entryKey}`);
        }
      });
      debugLog(
        `Processed ${rowCount} rows in materials grid, added ${materialEntries.length} entries`,
      );
    } else {
      debugLog(`Materials grid ${matKey} not found or missing API`);
    }
    sectionData.material_entries = materialEntries;
  }

  // ===================== 3) ADJUSTMENTS =====================
  {
    const adjKey = `simple${capitalize(section)}AdjustmentsTable`;
    const adjGrid = window.grids[adjKey];
    debugLog(
      `Processing simple adjustments grid ${adjKey}, exists: ${!!adjGrid}, has API: ${!!(adjGrid && adjGrid.api)}`,
    );

    let adjustmentEntries = [];
    const seenAdjustmentEntries = new Set();

    if (adjGrid && adjGrid.api) {
      let rowCount = 0;
      adjGrid.api.forEachNode((node) => {
        rowCount++;
        const row = node.data || {};
        const description = row.description?.trim() || "";
        const comments = row.comments?.trim() || "";
        const costAdj = parseFloat(row.cost_adjustment) || 0;
        const priceAdj = parseFloat(row.price_adjustment) || 0;

        const isEmptyRow = costAdj === 0 && priceAdj === 0;

        // Create unique key for adjustment entry
        const entryKey = `${description}-${costAdj}-${priceAdj}-${comments}`;
        debugLog(
          `Adjustment row ${rowCount}: "${description}", cost adj=${costAdj}, price adj=${priceAdj}, empty=${isEmptyRow}, duplicate=${seenAdjustmentEntries.has(entryKey)}`,
        );

        if (!isEmptyRow && !seenAdjustmentEntries.has(entryKey)) {
          const entry = {
            description: description,
            cost_adjustment: costAdj,
            price_adjustment: priceAdj,
            comments: comments,
          };
          adjustmentEntries.push(entry);
          seenAdjustmentEntries.add(entryKey);
        }
      });
      debugLog(
        `Processed ${rowCount} rows in adjustments grid, added ${adjustmentEntries.length} entries`,
      );
    }
    sectionData.adjustment_entries = adjustmentEntries;
  }

  return sectionData;
}

function collectCostsData() {
  const costsTable = window.grids.costsTable;
  if (!costsTable || !costsTable.api) {
    console.error("Costs table not found or missing API.");
    return { headers: [], rows: [] };
  }

  const gridApi = costsTable.api;
  const columns = gridApi
    .getColumnDefs()
    .filter((col) => col.headerName && col.headerName !== "Actions");
  const headers = columns.map((col) => col.headerName);

  const rowData = [];
  gridApi.forEachNode((node) => {
    const row = columns.map((col) => {
      const value = node.data[col.field];
      if (
        ["estimate", "quote", "reality"].includes(col.field) &&
        typeof value === "number"
      ) {
        return `$${value.toFixed(2)}`;
      }
      return value !== undefined ? value : "N/A";
    });
    rowData.push(row);
  });

  console.log("Collected Costs Data:", { headers, rows: rowData });

  return { headers, rows: rowData };
}

async function fetchImageAsBase64(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch image: ${response.statusText}`);
    }
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch (error) {
    console.error(`Error fetching image from ${url}:`, error);
    throw error;
  }
}

function processNotesHtml(html) {
  if (!html) return "N/A";

  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = html;

  function processNode(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent;
    }

    if (node.nodeType === Node.ELEMENT_NODE) {
      const children = Array.from(node.childNodes)
        .map(processNode)
        .filter(Boolean);

      if (children.length === 0) return null;

      const result = {
        text:
          children.length === 1 && typeof children[0] === "string"
            ? children[0]
            : children,
      };

      // Process style attributes if they exist
      if (node.style) {
        if (node.style.color) {
          result.color = node.style.color;
        }
        if (node.style.backgroundColor) {
          result.background = node.style.backgroundColor;
        }
        if (node.style.textAlign) {
          result.alignment = node.style.textAlign;
        }
      }

      switch (node.nodeName.toLowerCase()) {
        // Basic formatting
        case "strong":
        case "b":
          result.bold = true;
          break;
        case "em":
        case "i":
          result.italics = true;
          break;
        case "u":
          result.decoration = "underline";
          break;
        case "strike":
        case "s":
          result.decoration = "lineThrough";
          break;

        // Headers
        case "h1":
          result.fontSize = 24;
          result.bold = true;
          result.margin = [0, 10, 0, 5];
          break;
        case "h2":
          result.fontSize = 20;
          result.bold = true;
          result.margin = [0, 8, 0, 4];
          break;
        case "h3":
          result.fontSize = 18;
          result.bold = true;
          result.margin = [0, 6, 0, 3];
          break;
        case "h4":
          result.fontSize = 16;
          result.bold = true;
          result.margin = [0, 5, 0, 2];
          break;
        case "h5":
          result.fontSize = 14;
          result.bold = true;
          result.margin = [0, 4, 0, 2];
          break;
        case "h6":
          result.fontSize = 12;
          result.bold = true;
          result.margin = [0, 4, 0, 2];
          break;

        // Special blocks
        case "blockquote":
          return {
            text: children,
            italics: true,
            margin: [20, 5, 20, 5],
            color: "#666666",
            alignment: "left",
          };
        case "pre":
        case "code-block":
        case "code":
          return {
            text: children,
            font: "Courier",
            background: "#f4f4f4",
            fontSize: 10,
            margin: [5, 5, 5, 5],
            padding: [5, 5, 5, 5],
          };

        // Structure
        case "p":
          // Check for alignment defined via Quill classes
          if (node.classList.contains("ql-align-center")) {
            return {
              text: children,
              margin: [0, 0, 0, 5],
              alignment: "center",
            };
          } else if (node.classList.contains("ql-align-right")) {
            return { text: children, margin: [0, 0, 0, 5], alignment: "right" };
          } else if (node.classList.contains("ql-align-justify")) {
            return {
              text: children,
              margin: [0, 0, 0, 5],
              alignment: "justify",
            };
          }
          return { text: children, margin: [0, 0, 0, 5] };

        case "ul":
          return {
            ul: children.map((item) =>
              typeof item === "string" ? { text: item } : item,
            ),
          };
        case "ol":
          return {
            ol: children.map((item) =>
              typeof item === "string" ? { text: item } : item,
            ),
          };
        case "li":
          return result;

        // Indentation - handled via Quill classes
        default:
          // Check if it's a span or div with special Quill classes
          if (node.classList) {
            if (node.classList.contains("ql-indent-1"))
              result.margin = [20, 0, 0, 0];
            else if (node.classList.contains("ql-indent-2"))
              result.margin = [40, 0, 0, 0];
            else if (node.classList.contains("ql-indent-3"))
              result.margin = [60, 0, 0, 0];
            else if (node.classList.contains("ql-indent-4"))
              result.margin = [80, 0, 0, 0];

            // Check colors through Quill classes
            const colorClasses = Array.from(node.classList).filter(
              (cls) => cls.startsWith("ql-color-") || cls.startsWith("ql-bg-"),
            );

            colorClasses.forEach((cls) => {
              if (cls.startsWith("ql-color-")) {
                const color = cls.replace("ql-color-", "#");
                result.color = color;
              } else if (cls.startsWith("ql-bg-")) {
                const bgColor = cls.replace("ql-bg-", "#");
                result.background = bgColor;
              }
            });
          }
      }

      return result;
    }

    return null;
  }

  try {
    const processedContent = Array.from(tempDiv.childNodes)
      .map(processNode)
      .filter(Boolean);
    return processedContent.length > 0 ? processedContent : "N/A";
  } catch (error) {
    console.error("Error processing HTML notes for PDF:", error);
    return "Error processing formatted notes";
  }
}

async function exportJobToPDF(jobData) {
  return new Promise(async (resolve, reject) => {
    try {
      const logoBase64 = await fetchImageAsBase64("/static/logo_msm.png");

      const pricingSections = [
        {
          section: "Estimate",
          grids: [
            { name: "estimateTimeTable", label: "Time" },
            { name: "estimateMaterialsTable", label: "Materials" },
            { name: "estimateAdjustmentsTable", label: "Adjustments" },
          ],
        },
        {
          section: "Quote",
          grids: [
            { name: "quoteTimeTable", label: "Time" },
            { name: "quoteMaterialsTable", label: "Materials" },
            { name: "quoteAdjustmentsTable", label: "Adjustments" },
          ],
        },
        {
          section: "Reality",
          grids: [
            { name: "realityTimeTable", label: "Time" },
            { name: "realityMaterialsTable", label: "Materials" },
            { name: "realityAdjustmentsTable", label: "Adjustments" },
          ],
        },
      ];

      const pricingContent = pricingSections
        .map(({ section, grids }) => {
          const sectionContent = [
            { text: section, style: "sectionHeader", margin: [0, 20, 0, 10] },
          ];

          grids.forEach((grid) => {
            const gridInstance = window.grids[grid.name];
            if (!gridInstance || !gridInstance.api) {
              sectionContent.push({
                text: `Grid '${grid.name}' not found or missing API.`,
                style: "error",
              });
              return;
            }

            sectionContent.push({
              text: grid.label,
              style: "gridHeader",
              margin: [0, 10, 0, 5],
            });

            const gridApi = gridInstance.api;
            const columns = gridApi
              .getColumnDefs()
              .filter(
                (col) =>
                  col.headerName !== "" && col.headerName !== "Timesheet",
              );
            const headers = columns.map((col) => col.headerName || "N/A");

            const rowData = [];
            gridApi.forEachNode((node) => {
              const row = columns.map((col) => {
                const value = node.data[col.field];
                if (
                  [
                    "cost",
                    "revenue",
                    "price_adjustment",
                    "cost_adjustment",
                  ].includes(col.field) &&
                  typeof value === "number"
                ) {
                  return `$${value.toFixed(2)}`;
                }
                return value || "N/A";
              });
              rowData.push(row);
            });

            if (rowData.length > 0) {
              sectionContent.push({
                table: {
                  headerRows: 1,
                  widths: Array(headers.length).fill("*"),
                  body: [
                    headers.map((header) => ({
                      text: header,
                      fillColor: "#004aad",
                      color: "#ffffff",
                      bold: true,
                      fontSize: 12,
                    })),
                    ...rowData,
                  ],
                },
                margin: [0, 5, 0, 15],
              });
            } else {
              sectionContent.push({
                text: `No data available for '${grid.label}'.`,
                style: "error",
              });
            }
          });

          return sectionContent;
        })
        .flat();

      const revenueAndCostsContent = ["revenueTable", "costsTable"]
        .map((gridKey) => {
          const grid = window.grids[gridKey];
          if (!grid || !grid.api) {
            return {
              text: `Grid '${gridKey}' not found or missing API.`,
              style: "error",
            };
          }

          const title =
            gridKey === "revenueTable" ? "Revenue Details" : "Costs Details";
          const gridApi = grid.api;
          const columns = gridApi
            .getColumnDefs()
            .filter(
              (col) => col.headerName !== "" && col.headerName !== "Timesheet",
            );
          const headers = columns.map((col) => col.headerName || "N/A");

          const rowData = [];
          gridApi.forEachNode((node) => {
            const row = columns.map((col) => {
              const value = node.data[col.field];
              if (
                ["estimate", "quote", "reality"].includes(col.field) &&
                typeof value === "number"
              ) {
                return `$${value.toFixed(2)}`;
              }
              return value || "N/A";
            });
            rowData.push(row);
          });

          return [
            { text: title, style: "sectionHeader", margin: [0, 20, 0, 10] },
            {
              table: {
                headerRows: 1,
                widths: Array(headers.length).fill("*"),
                body: [
                  headers.map((header) => ({
                    text: header,
                    fillColor: "#004aad",
                    color: "#ffffff",
                    bold: true,
                    fontSize: 12,
                  })),
                  ...rowData,
                ],
              },
              margin: [0, 5, 0, 15],
            },
          ];
        })
        .flat();

      const docDefinition = {
        content: [
          {
            image: logoBase64,
            width: 150,
            alignment: "center",
            margin: [0, 0, 0, 20],
          },
          {
            text: "Job Summary",
            style: "header",
            margin: [0, 0, 0, 20],
          },
          {
            text: `Generated on: ${new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}`,
            style: "subheader",
            alignment: "right",
          },
          {
            text: "Job Details",
            style: "sectionHeader",
            margin: [0, 20, 0, 10],
          },
          {
            table: {
              headerRows: 1,
              widths: ["*", "*"],
              body: [
                [
                  {
                    text: "Field",
                    fillColor: "#004aad",
                    color: "#ffffff",
                    bold: true,
                  },
                  {
                    text: "Value",
                    fillColor: "#004aad",
                    color: "#ffffff",
                    bold: true,
                  },
                ],
                ["Job Name", jobData.name || "N/A"],
                ["Job Number", jobData.job_number || "N/A"],
                ["Client", jobData.client_name || "N/A"],
                ["Contact Person", jobData.contact_person || "N/A"],
                ["Description", jobData.description || "N/A"],
                ["Notes", processNotesHtml(jobData.notes)],
                [
                  "Job Created On",
                  new Date(jobData.created_at).toLocaleDateString("en-US", {
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  }) || "N/A",
                ],
              ],
            },
            margin: [0, 0, 0, 20],
          },
          ...pricingContent,
          ...revenueAndCostsContent,
        ],
        styles: {
          header: { fontSize: 22, bold: true, alignment: "center" },
          subheader: { fontSize: 12, italic: true },
          sectionHeader: { fontSize: 16, bold: true, margin: [0, 20, 0, 10] },
          gridHeader: { fontSize: 14, bold: true, color: "#444444" },
          error: { fontSize: 12, color: "red", italic: true },
        },
      };

      pdfMake.createPdf(docDefinition).getBlob((blob) => {
        resolve(blob);
      });
    } catch (error) {
      console.error("Error generating Job PDF:", error);
    }
  });
}

async function exportCostsToPDF(costsData, jobData) {
  try {
    const logoBase64 = await fetchImageAsBase64("/static/logo_msm.png");
    const docDefinition = {
      content: [
        {
          image: logoBase64,
          width: 150,
          alignment: "center",
          margin: [0, 0, 0, 20],
        },
        {
          text: "Costs Summary",
          style: "header",
          margin: [0, 0, 0, 20],
        },
        {
          text: `Generated on: ${new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}`,
          style: "subheader",
          alignment: "right",
        },
        { text: "Job Summary", style: "sectionHeader", margin: [0, 20, 0, 10] },
        {
          table: {
            headerRows: 1,
            widths: ["*", "*"],
            body: [
              ["Field", "Value"],
              ["Job Name", jobData.name || "N/A"],
              ["Job Number", jobData.job_number || "N/A"],
              ["Client", jobData.client_name || "N/A"],
              [
                "Created At",
                new Date(jobData.created_at).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                }) || "N/A",
              ],
              ["Description", jobData.description || "N/A"],
            ],
          },
        },
        {
          text: "Cost Details",
          style: "sectionHeader",
          margin: [0, 20, 0, 10],
        },
        {
          table: {
            headerRows: 1,
            widths: ["*", "auto", "auto", "auto"],
            body: [costsData.headers, ...costsData.rows],
          },
        },
      ],
      styles: {
        header: { fontSize: 22, bold: true, alignment: "center" },
        subheader: { fontSize: 12, italic: true },
        sectionHeader: { fontSize: 16, bold: true, margin: [0, 20, 0, 10] },
      },
    };

    pdfMake.createPdf(docDefinition).open();
  } catch (error) {
    console.error("Error fetching logo:", error);
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

async function handlePDF(pdfBlob, mode, jobData) {
  const pdfURL = URL.createObjectURL(pdfBlob);
  const pdfFileName = `JobSummary.pdf`;

  switch (mode) {
    case "upload":
      try {
        console.log("Starting PDF upload process for job:", jobData.job_number);
        const fileExists = await checkExistingJobFile(
          jobData.job_number,
          pdfFileName,
        );
        console.log("File exists check result:", fileExists);

        await uploadJobFile(
          jobData.job_number,
          new File([pdfBlob], pdfFileName, { type: "application/pdf" }),
          fileExists ? "PUT" : "POST",
        );

        console.log("PDF upload completed successfully");
      } catch (error) {
        console.error("Error during file upload:", error);
        throw error;
      }
      break;
    case "print":
      const newWindow = window.open(pdfURL, "_blank");
      if (!newWindow)
        throw new Error("Popup blocked. Unable to print the PDF.");
      newWindow.print();
      break;
    case "preview":
      window.open(pdfURL, "_blank");
      break;
    case "download":
      const link = document.createElement("a");
      link.href = pdfURL;
      link.download = `${jobData.name}.pdf`;
      link.click();
      break;
    default:
      throw new Error(`Unsupported mode: ${mode}`);
  }
}

function addJobDetailsToPDF(doc, jobData) {
  let startY = 10;

  // Job Details section
  doc.setFontSize(16);
  doc.text("Job Details", 10, startY);
  doc.setFontSize(12);
  startY += 10;

  // Add job details table
  const jobDetailsData = [
    ["Job Number", jobData.job_number || ""],
    ["Client", jobData.client_name || ""],
    ["Contact Person", jobData.contact_person || ""],
    ["Contact Phone", jobData.contact_phone || ""],
    ["Description", jobData.description || ""],
  ];

  doc.autoTable({
    body: jobDetailsData,
    startY: startY,
  });

  return doc.lastAutoTable.finalY + 10;
}

function exportJobToWorkshopPDF(jobData) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();

  // Add job details
  let startY = addJobDetailsToPDF(doc, jobData);

  // Add files marked for printing
  const printCheckboxes = document.querySelectorAll(
    ".print-on-jobsheet:checked",
  );
  if (printCheckboxes.length > 0) {
    doc.setFontSize(16);
    doc.text("Attached Files", 10, startY);
    doc.setFontSize(12);
    startY += 10;

    printCheckboxes.forEach((checkbox) => {
      const fileCard = checkbox.closest(".file-card");
      const fileLink = fileCard.querySelector("a");
      const fileName = fileLink.textContent.trim();

      doc.text(fileName, 10, startY);
      startY += 10;

      // If it's an image, try to add it to the PDF
      if (fileName.match(/\.(jpg|jpeg|png|gif)$/i)) {
        const img = new Image();
        img.src = fileLink.href;
        try {
          doc.addImage(img, "JPEG", 10, startY, 180, 0);
          startY += 100; // Adjust based on image height
        } catch (error) {
          console.error("Failed to add image to PDF:", error);
        }
      }
    });
  }

  return new Blob([doc.output("blob")], { type: "application/pdf" });
}

export async function handlePrintWorkshop() {
  try {
    // Collect the current job data
    const collectedData = collectAllData();

    // Validate the job before proceeding
    if (!collectedData.job_is_valid) {
      console.error(
        "Job is not valid. Please complete all required fields before printing.",
      );
      return;
    }

    // Get the job ID from the URL
    const jobId = window.location.pathname.split("/").filter(Boolean).pop();

    // Get and print the workshop PDF (which now includes all marked files)
    const workshopResponse = await fetch(`/job/${jobId}/workshop-pdf/`);
    if (!workshopResponse.ok) {
      throw new Error("Failed to generate workshop PDF");
    }
    const workshopBlob = await workshopResponse.blob();
    const workshopUrl = URL.createObjectURL(workshopBlob);
    const workshopWindow = window.open(workshopUrl, "_blank");
    if (!workshopWindow) {
      throw new Error(
        "Popup blocked. Please allow popups to print the workshop sheet.",
      );
    }
    workshopWindow.print();
  } catch (error) {
    console.error("Error during Print Workshop process:", error);
    alert(`Error printing: ${error.message}`);
  }
}

export function handleExportCosts() {
  try {
    const jobData = collectAllData();
    const costsData = collectCostsData();

    if (!jobData.job_is_valid) {
      console.error("Job is not valid. Complete all required fields.");
      return;
    }

    exportCostsToPDF(costsData, jobData);
  } catch (error) {
    console.error("Error exporting costs with PDFMake:", error);
  }
}

// Autosave function to send data to the server
export function autosaveData() {
  // Prevent autosave when viewing historical data
  if (window.isInHistoricalMode && window.isInHistoricalMode()) {
    console.log("Autosave disabled while viewing historical data");
    return;
  }

  const collectedData = collectAllData();

  // Skip autosave if the job is not yet ready for saving
  if (!collectedData.job_is_valid) {
    console.log("Job is not valid. Skipping autosave.");
    renderMessages(
      [
        {
          level: "error",
          message: "Please complete all required fields before saving.",
        },
      ],
      "job-details",
    );
    return;
  }
  // Only save if the job is valid
  saveDataToServer(collectedData);
}

function saveDataToServer(collectedData) {
  if (!checkJobValidity(collectedData)) {
    console.error("Collected data is invalid. Skipping autosave.");
    return;
  }

  console.log("Autosaving data to /api/autosave-job/...", collectedData);

  fetch("/api/autosave-job/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify(collectedData),
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((data) => {
          if (data.errors) {
            handleValidationErrors(data.errors);
            const errorMsg = extractErrorMessages(data.errors);
            renderMessages(
              [
                {
                  level: "error",
                  message: "Autosave failed: " + errorMsg,
                },
              ],
              "job-details",
            );
          }
        });
      }
      return response.json();
    })
    .then((data) => {
      exportJobToPDF(collectedData).then((pdfBlob) => {
        handlePDF(pdfBlob, "upload", collectedData);
        console.log("Autosave successful:", data);

        calculateTotalRevenue();
        calculateTotalCost();
        calculateSimpleTotals();

        renderMessages(
          [{ level: "success", message: "Job updated successfully." }],
          "job-details",
        );
      });
    })
    .catch((error) => {
      renderMessages(
        [{ level: "error", message: `Autosave failed: ${error.message}` }],
        "job-details",
      );
    });
}

// Function to extract error messages from a nested error structure
function extractErrorMessages(errors) {
  // Handle simple string error case
  if (typeof errors === "string") return errors;

  // Array case - use flatMap to avoid nesting
  if (Array.isArray(errors)) {
    return errors
      .flatMap((error) => {
        if (!error) return [];
        if (typeof error !== "object") return String(error);

        // Extract message or delegate to recursive call
        return error.message || error.string || extractErrorMessages(error);
      })
      .filter(Boolean)
      .join(". ");
  }

  // Object case - collect all nested errors
  if (errors && typeof errors === "object") {
    return Object.values(errors)
      .flatMap((value) => extractErrorMessages(value))
      .filter(Boolean)
      .join(". ");
  }

  return "";
}

function handleValidationErrors(errors) {
  // Clear previous error messages
  document
    .querySelectorAll(".invalid-feedback")
    .forEach((errorMsg) => errorMsg.remove());
  document
    .querySelectorAll(".is-invalid")
    .forEach((el) => el.classList.remove("is-invalid"));

  // Display new errors
  for (const [field, messages] of Object.entries(errors)) {
    const element = document.querySelector(`[name='${field}']`);
    if (element) {
      element.classList.add("is-invalid");
      const errorDiv = document.createElement("div");
      errorDiv.className = "invalid-feedback";

      element.parentElement.appendChild(errorDiv);

      // Attach listener to remove the error once the user modifies the field
      element.addEventListener(
        "input",
        () => {
          element.classList.remove("is-invalid");
          if (
            element.nextElementSibling &&
            element.nextElementSibling.classList.contains("invalid-feedback")
          ) {
            element.nextElementSibling.remove();
          }
        },
        { once: true },
      );
    }
  }
}

// Helper function to get CSRF token for Django
function getCsrfToken() {
  return document.querySelector("[name=csrfmiddlewaretoken]").value;
}

function removeValidationError(element) {
  element.classList.remove("is-invalid");
  if (
    element.nextElementSibling &&
    element.nextElementSibling.classList.contains("invalid-feedback")
  ) {
    element.nextElementSibling.remove();
  }
}

// Debounced version of the autosave function
export const debouncedAutosave = debounce(function () {
  console.log("Debounced autosave called");
  autosaveData();
}, 1000);

const debouncedRemoveValidation = debounce(function (element) {
  console.log("Debounced validation removal called for element:", element);
  removeValidationError(element);
}, 1000);

// Attach autosave to form elements (input, select, textarea)
// Synchronize visible UI fields with hidden form fields
// Handle close button functionality
async function handleClose() {
  try {
    // 1. Trigger autosave
    const collectedData = collectAllData();
    if (!collectedData.job_is_valid) {
      console.error(
        "Job is not valid. Please complete all required fields before closing.",
      );
      renderMessages(
        [
          {
            level: "error",
            message: "⚠️ You must complete all required fields before closing.",
          },
        ],
        "job-details",
      );
      return;
    }

    console.log("Collected data before closing:", collectedData);

    // Save and wait for completion
    await fetch("/api/autosave-job/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(collectedData),
    });

    // 2. Generate PDF
    const pdfBlob = await exportJobToPDF(collectedData);

    // 3. Check if JobSummary.pdf already exists and upload/update accordingly
    const fileExists = await checkExistingJobFile(
      collectedData.job_number,
      "JobSummary.pdf",
    );
    await uploadJobFile(
      collectedData.job_number,
      new File([pdfBlob], "JobSummary.pdf", { type: "application/pdf" }),
      fileExists ? "PUT" : "POST",
    );

    // 4. Redirect back to kanban
    window.location.href = "/";
  } catch (error) {
    console.error("Error during close process:", error);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  // Synchronize all elements with the 'autosave-input' class
  const autosaveInputs = document.querySelectorAll(".autosave-input");

  // Add close button handler
  const closeButton = document.getElementById("closeButton");
  if (closeButton) {
    closeButton.addEventListener("click", handleClose);
  }

  // Attach change event listener to handle special input types like checkboxes
  autosaveInputs.forEach((fieldElement) => {
    fieldElement.addEventListener("blur", function () {
      console.log("Blur event fired for:", fieldElement);
      debouncedRemoveValidation(fieldElement);
      debouncedAutosave();
    });

    if (fieldElement.type === "checkbox" || fieldElement.tagName === "SELECT") {
      fieldElement.addEventListener("change", function () {
        if (fieldElement.classList.contains("is-invalid")) {
          fieldElement.classList.remove("is-invalid");
        }
        debouncedRemoveValidation(fieldElement);
        debouncedAutosave();
      });
    }
  });

  // Initialize historical navigation
  initHistoricalNavigation();
});

function getAllRowData(gridApi) {
  const rowData = [];
  gridApi.forEachNode((node) => rowData.push(node.data));
  return rowData;
}

function copyGridData(sourceGridApi, targetGridApi) {
  if (!sourceGridApi || !targetGridApi) {
    console.error("Source or target grid API is not defined.");
    return;
  }

  const sourceData = getAllRowData(sourceGridApi);
  const targetData = getAllRowData(targetGridApi);

  targetGridApi.applyTransaction({ remove: targetData });
  targetGridApi.applyTransaction({ add: sourceData });
}

export function copyEstimateToQuote() {
  try {
    // Determine if we're in simple or complex mode
    const isComplex =
      document.getElementById("complex-job").textContent.toLowerCase() ===
      "true";
    console.log(
      `Copy estimate to quote - Mode: ${isComplex ? "Complex" : "Simple"}`,
    );

    const grids = ["TimeTable", "MaterialsTable", "AdjustmentsTable"];

    grids.forEach((gridName) => {
      // Select the correct grid keys based on the mode
      const estimateGridKey = isComplex
        ? `estimate${gridName}`
        : `simpleEstimate${gridName}`;
      const quoteGridKey = isComplex
        ? `quote${gridName}`
        : `simpleQuote${gridName}`;

      const estimateGridApi = window.grids[estimateGridKey]?.api;
      const quoteGridApi = window.grids[quoteGridKey]?.api;

      console.log(
        `Attempting to copy from ${estimateGridKey} to ${quoteGridKey}`,
      );

      if (estimateGridApi && quoteGridApi) {
        copyGridData(estimateGridApi, quoteGridApi);
        console.log(
          `Successfully copied data from ${estimateGridKey} to ${quoteGridKey}`,
        );
      } else {
        console.error(
          `Grid API not found for keys: ${estimateGridKey}, ${quoteGridKey}`,
        );
      }
    });

    // Update calculations and trigger autosave
    calculateTotalRevenue();
    calculateTotalCost();
    calculateSimpleTotals();
    debouncedAutosave();

    renderMessages(
      [
        {
          level: "success",
          message: "Estimates successfully copied to quotes.",
        },
      ],
      "estimate",
    );
  } catch (error) {
    console.error("Error copying from estimates to quotes:", error);
    renderMessages(
      [
        {
          level: "error",
          message: `Failed copying from estimates to quotes: ${error.message}`,
        },
      ],
      "estimate",
    );
  }
}
