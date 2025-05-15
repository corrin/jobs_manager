// deserialize_job_pricing.js
import { Environment } from "../env.js";

document.addEventListener("DOMContentLoaded", function () {
  const latestJobPricingsElement = document.getElementById(
    "latestJobPricingsData",
  );
  if (latestJobPricingsElement) {
    try {
      if (Environment.isDebugMode()) {
        console.log(
          "Debug: Raw latestJobPricingsData content:",
          JSON.parse(latestJobPricingsElement.textContent),
        );
      }
      window.latest_job_pricings_json = JSON.parse(
        latestJobPricingsElement.textContent,
      );
    } catch (error) {
      console.error("Failed to parse latest job pricing data:", error);
    }
  } else {
    console.error("Could not find latest job pricing data.");
  }
});

document.addEventListener("DOMContentLoaded", function () {
  const historicalJobPricingsElement = document.getElementById(
    "historicalJobPricingsData",
  );
  if (historicalJobPricingsElement) {
    try {
      window.historical_job_pricings_json = JSON.parse(
        historicalJobPricingsElement.textContent,
      );
    } catch (error) {
      console.error("Failed to parse Historical job pricing data:", error);
    }
  } else {
    console.error("Could not find historical job pricing data.");
  }
});

/**
 * Retrieves row data for a given section/gridType from the latest_job_pricings_json.
 * Creates a new row if no data is found.
 */
export function getGridData(section, gridType) {
  if (!window.latest_job_pricings_json) {
    console.error("Error: latest_job_pricings_json data is not loaded.");
    return [createNewRow(gridType)];
  }

  const sectionKey = `${section}_pricing`;
  const sectionData = window.latest_job_pricings_json[sectionKey];

  let effectiveGridType = gridType;
  if (section === "reality" && gridType.startsWith("Simple")) {
    // Converting simple to complex when reality section is detected
    effectiveGridType = gridType.replace("Simple", "");
    if (Environment.isDebugMode()) {
      console.log(
        `Reality section detected. Converting grid type from ${gridType} to ${effectiveGridType}`,
      );
    }
  }

  if (!sectionData) {
    // Section not found -> new row
    if (Environment.isDebugMode()) {
      console.log(
        `Debug: No data found for section ${sectionKey}, creating new row`,
      );
    }
    return [createNewRow(effectiveGridType)];
  }

  // Convert "SimpleXYZTable" => "XYZTable" for internal usage
  let realGridType = effectiveGridType;
  if (effectiveGridType.startsWith("Simple")) {
    realGridType = effectiveGridType.replace("Simple", "");
  }

  // Convert e.g. "TimeTable" => "time_entries", "MaterialsTable" => "material_entries", etc.
  const gridBaseName = realGridType.toLowerCase().replace("table", "");
  const entryType =
    (gridBaseName === "materials"
      ? "material"
      : gridBaseName === "adjustments"
        ? "adjustment"
        : gridBaseName) + "_entries";

  // If no data found, create new row
  if (!sectionData[entryType] || sectionData[entryType].length === 0) {
    if (Environment.isDebugMode()) {
      console.log(
        `[getGridData]: No ${entryType} found in section ${sectionKey}, creating new row`,
      );
    }
    return [createNewRow(gridType)];
  }

  if (Environment.isDebugMode())
    console.log(
      `Loading existing ${entryType} for ${sectionKey} | ${effectiveGridType}`,
    );
  return loadExistingJobEntries(sectionData[entryType], effectiveGridType);
}

/**
 * Delegates loading of existing job entries to the appropriate loader function (advanced vs. simple).
 */
function loadExistingJobEntries(entries, gridType) {
  switch (gridType) {
    case "TimeTable":
      return loadAdvJobTime(entries);
    case "MaterialsTable":
      return loadAdvJobMaterial(entries);
    case "AdjustmentsTable":
      return loadAdvJobAdjustment(entries);

    case "SimpleTimeTable":
      return loadSimpleJobTime(entries);
    case "SimpleMaterialsTable":
      return loadSimpleJobMaterial(entries);
    case "SimpleAdjustmentsTable":
      return loadSimpleJobAdjustment(entries);

    default:
      console.error(`Unknown grid type: "${gridType}"`);
      return [createNewRow(gridType)];
  }
}

// Advanced loaders
function loadAdvJobTime(entries) {
  return entries.map((entry) => {
    const hours = (entry.total_minutes / 60).toFixed(1);
    const formattedTotalMinutes = `${entry.total_minutes} (${hours} hours)`;

    console.log("[-loadAdvJobTime] entry:", entry);

    return {
      description: entry.description,
      items: entry.items,
      mins_per_item: entry.minutes_per_item,
      wage_rate: entry.wage_rate !== "0.00" ? entry.wage_rate : 32,
      charge_out_rate: entry.charge_out_rate,
      total_minutes: formattedTotalMinutes,
      revenue: entry.revenue,
      link:
        entry.timesheet_date && entry.staff_id
          ? `/timesheets/day/${entry.timesheet_date}/${entry.staff_id}`
          : "/timesheets/overview/",
      staff_name:
        entry.staff_name,
    };
  });
}

function loadAdvJobMaterial(entries) {
  return entries.map((entry) => ({
    item_code: entry.item_code,
    description: entry.description,
    quantity: entry.quantity,
    unit_cost: entry.unit_cost,
    unit_revenue: entry.unit_revenue,
    revenue: entry.revenue,
    comments: entry.comments,
  }));
}

function loadAdvJobAdjustment(entries) {
  return entries.map((entry) => ({
    description: entry.description,
    cost_adjustment: entry.cost_adjustment,
    price_adjustment: entry.price_adjustment,
    comments: entry.comments,
    revenue: entry.revenue,
  }));
}

// Simple loaders
function loadSimpleJobTime(entries) {
  return entries.map((entry) => {
    const hours = parseFloat(entry.total_minutes / 60) || 0;
    const wage = parseFloat(entry.wage_rate) || 32;
    const charge = parseFloat(entry.charge_out_rate) || 105;

    return {
      description: "",
      hours: hours,
      cost_of_time: hours * wage,
      value_of_time: hours * charge,
      wage_rate: wage,
      charge_out_rate: charge,
    };
  });
}

function loadSimpleJobMaterial(entries) {
  return entries.map((entry) => ({
    description: "",
    material_cost: entry.unit_cost * entry.quantity,
    retail_price: entry.unit_revenue * entry.quantity,
  }));
}

function loadSimpleJobAdjustment(entries) {
  return entries.map((entry) => ({
    description: "",
    cost_adjustment: entry.cost_adjustment,
    price_adjustment: entry.price_adjustment,
  }));
}

/**
 * Creates a default row for the given grid type.
 * If unknown grid type, returns an empty object.
 */
export function createNewRow(gridType) {
  const companyDefaults = document.getElementById("companyDefaults");
  if (!companyDefaults) {
    // If there's no defaults element, fallback to some zeros
    return {};
  }
  const defaultWageRate = parseFloat(companyDefaults.dataset.wageRate);
  const defaultChargeOutRate = parseFloat(
    companyDefaults.dataset.chargeOutRate,
  );

  switch (gridType) {
    // Advanced
    case "TimeTable":
      return {
        description: "",
        items: 1,
        mins_per_item: 0,
        wage_rate: defaultWageRate,
        charge_out_rate: defaultChargeOutRate,
        total_minutes: 0,
        total_minutes_display: "0 (0.0 hours)",
        revenue: 0,
      };
    case "MaterialsTable":
      return {
        item_code: "",
        description: "",
        quantity: 1,
        unit_cost: 0,
        unit_revenue: 0,
        isManualOverride: false,
        revenue: 0,
        comments: "",
      };
    case "AdjustmentsTable":
      return {
        description: "",
        cost_adjustment: 0,
        price_adjustment: 0,
        comments: "",
        revenue: 0,
      };

    // Simple
    case "SimpleTimeTable":
      return {
        description: "",
        hours: 0,
        cost_of_time: 0,
        value_of_time: 0,
        wage_rate: defaultWageRate,
        charge_out_rate: defaultChargeOutRate,
      };
    case "SimpleMaterialsTable":
      return {
        description: "",
        material_cost: 0,
        retail_price: 0,
        isManualOverride: false,
      };
    case "SimpleAdjustmentsTable":
      return {
        description: "",
        cost_adjustment: 0,
        price_adjustment: 0,
        isManualOverride: false,
      };
    case "SimpleTotalTable":
      return {
        cost: 0,
        retail: 0,
      };
    default:
      console.error(`Unknown grid type for new row creation: "${gridType}"`);
      return {};
  }
}
