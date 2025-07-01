export function currencyFormatter(params) {
  if (params.value === undefined) {
    // console.error('currencyFormatter error: value is undefined for the following params:', params);
    return "$0.00"; // Return a fallback value so the grid doesn't break
  }
  return (
    "$" +
    params.value.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

export function numberParser(params) {
  const value = params.newValue;

  // Handle null, undefined, or empty string
  if (value === null || value === undefined || value === '') {
    return 0;
  }

  // Convert to string for processing
  const stringValue = String(value);

  // Remove currency symbols, commas, and whitespace
  // This handles formats like: $1,234.56, $1234.56, 1,234.56, 1234.56, etc.
  const cleanValue = stringValue
    .replace(/[$,\s]/g, '')  // Remove dollar signs, commas, and whitespace
    .trim();

  // Parse the cleaned value
  const parsed = parseFloat(cleanValue);

  // Return 0 if parsing failed (NaN)
  if (isNaN(parsed)) {
    return 0;
  }

  // Round to 2 decimal places to match database precision
  return Math.round(parsed * 100) / 100;
}

export function currencyParser(params) {
  // Currency parser - same logic as numberParser but with better error handling for currency
  const value = params.newValue;

  // Handle null, undefined, or empty string
  if (value === null || value === undefined || value === '') {
    return 0;
  }

  // Convert to string for processing
  const stringValue = String(value);

  // Remove currency symbols, commas, and whitespace
  // This handles formats like: $1,234.567, ($1,234.56), -$1,234.56, etc.
  let cleanValue = stringValue
    .replace(/[\$,\s()]/g, '')  // Remove dollar signs, commas, whitespace, and parentheses
    .trim();

  // Handle negative values in parentheses (accounting format)
  const isNegative = stringValue.includes('(') && stringValue.includes(')');

  // Parse the cleaned value
  const parsed = parseFloat(cleanValue);

  // Return 0 if parsing failed (NaN)
  if (isNaN(parsed)) {
    return 0;
  }

  // Apply negative sign if value was in parentheses
  const result = isNegative ? -parsed : parsed;

  // Round to 2 decimal places to match database precision
  return Math.round(result * 100) / 100;
}
