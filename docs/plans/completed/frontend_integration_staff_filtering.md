# Frontend Integration: Staff Date-Based Filtering System

## Overview

The backend has implemented a new staff date-based filtering system that replaces the inconsistent `is_active` boolean field with a proper `date_left` field. This enables accurate historical queries like "who was employed on date X".

## Critical API Changes

### 1. Timesheet Staff API - BREAKING CHANGE ⚠️

**Endpoint**: `/api/timesheet/staff/`

**BEFORE** (deprecated):

```javascript
// This will now return 400 Bad Request
fetch("/api/timesheet/staff/");
```

**AFTER** (required):

```javascript
// Must include date parameter for historical accuracy
const targetDate = "2024-07-31"; // YYYY-MM-DD format
fetch(`/api/timesheet/staff/?date=${targetDate}`);
```

**Response Format** (unchanged):

```json
{
  "staff": [
    {
      "id": "uuid",
      "name": "Full Name",
      "firstName": "First",
      "lastName": "Last"
    }
  ]
}
```

### 2. Accounts Staff API - Enhanced

**Endpoint**: `/api/accounts/staff/`

**Current Staff** (default - no changes needed):

```javascript
// Shows currently active staff (date_left is null or future)
fetch("/api/accounts/staff/");
```

**Historical Staff** (new capability):

```javascript
// Shows staff who were active on specific date
const historicalDate = "2024-01-15";
fetch(`/api/accounts/staff/?date=${historicalDate}`);
```

**All Staff Including Inactive** (new capability):

```javascript
// Shows all staff regardless of active status
fetch("/api/accounts/staff/?include_inactive=true");
```

## Required Frontend Updates

### 1. Weekly Timesheet View

**Location**: Timesheet components that display weekly staff data

**Current Issue**: Likely making requests without date parameter

**Required Fix**:

```javascript
// BEFORE (will fail)
const fetchStaffForWeek = () => {
  return fetch("/api/timesheet/staff/");
};

// AFTER (required)
const fetchStaffForWeek = (weekDate) => {
  // Use the Monday of the week or specific date
  const dateStr = weekDate.toISOString().split("T")[0]; // YYYY-MM-DD
  return fetch(`/api/timesheet/staff/?date=${dateStr}`);
};
```

**Implementation Notes**:

- Pass the Monday of the target week or any date within the week
- The API returns staff who were employed on that specific date
- This ensures historical accuracy for past timesheet weeks

### 2. Kanban Staff Icons

**Location**: Job Kanban board showing staff member icons

**Good News**: No changes required if using default behavior

**Current Code** (should work unchanged):

```javascript
// This continues to work - shows currently active staff
const fetchCurrentStaff = () => {
  return fetch("/api/accounts/staff/");
};
```

**Verification**: Ensure you're not passing `is_active=true` parameter (no longer exists)

### 3. Staff Selection Components

**Location**: Any dropdowns or selectors for staff members

**Default Behavior** (recommended):

```javascript
// Shows currently active staff for most use cases
const fetchStaffOptions = () => {
  return fetch("/api/accounts/staff/");
};
```

**Historical Context** (if needed):

```javascript
// For editing historical records, show staff active at that time
const fetchStaffForDate = (recordDate) => {
  const dateStr = recordDate.toISOString().split("T")[0];
  return fetch(`/api/accounts/staff/?date=${dateStr}`);
};
```

## Data Model Changes

### Staff Object Structure

**REMOVED Fields**:

```javascript
// ❌ No longer available
staff.is_active; // Boolean field removed
```

**ADDED Fields**:

```javascript
// ✅ New fields available
staff.date_left; // String (YYYY-MM-DD) or null
staff.is_currently_active; // Boolean (computed property)
```

**Usage Examples**:

```javascript
// Check if staff member is currently active
if (staff.is_currently_active) {
  // Staff member is currently employed
}

// Check when staff member left (if applicable)
if (staff.date_left) {
  console.log(`Staff left on ${staff.date_left}`);
} else {
  console.log("Staff is currently active");
}
```

## Implementation Priority

### High Priority (Breaking Changes)

1. **Fix Timesheet Views**: Update all weekly/daily timesheet components to pass date parameter
2. **Test Current Functionality**: Verify Kanban staff icons still work

### Medium Priority (Enhancements)

1. **Update Staff Model Types**: Update TypeScript interfaces if using typed frontend
2. **Historical Staff Queries**: Implement date-based staff selection for editing historical records

### Low Priority (Nice to Have)

1. **Staff Status Indicators**: Show visual indicators for active/inactive status
2. **Date Range Queries**: Implement staff filtering for date ranges if needed

## Error Handling

### API Error Responses

**Missing Date Parameter** (Timesheet API):

```json
{
  "error": "Date parameter is required for historical staff accuracy. Provide date in YYYY-MM-DD format."
}
```

**Invalid Date Format**:

```json
{
  "error": "Invalid date format. Expected YYYY-MM-DD."
}
```

**Frontend Error Handling**:

```javascript
const fetchStaffWithErrorHandling = async (date) => {
  try {
    const response = await fetch(`/api/timesheet/staff/?date=${date}`);
    if (!response.ok) {
      const error = await response.json();
      console.error("Staff API Error:", error.error);
      // Show user-friendly error message
      throw new Error("Unable to load staff data");
    }
    return await response.json();
  } catch (error) {
    // Handle network errors, invalid JSON, etc.
    console.error("Failed to fetch staff:", error);
    throw error;
  }
};
```

## Testing Checklist

### Functional Testing

- [ ] Weekly timesheet shows correct staff for current week
- [ ] Weekly timesheet shows correct staff for historical weeks
- [ ] Kanban board shows only currently active staff
- [ ] Staff dropdowns work for creating new records
- [ ] Error handling works when date parameter is missing

### Edge Case Testing

- [ ] Staff member who joined mid-week appears correctly
- [ ] Staff member who left mid-week appears correctly
- [ ] Future dates return appropriate staff list
- [ ] Invalid date formats show proper error messages

## Migration Strategy

### Phase 1: Fix Breaking Changes

1. Identify all components calling `/api/timesheet/staff/`
2. Update to include date parameter
3. Test with current date first

### Phase 2: Enhance Historical Accuracy

1. Update timesheet views to use appropriate historical dates
2. Test with various past dates
3. Verify staff lists match employment records

### Phase 3: UI Improvements

1. Update staff model interfaces/types
2. Add visual indicators for staff status
3. Implement enhanced filtering options

## Backend Contact Points

If you encounter issues or need clarification:

1. **API Documentation**: Check `/api/schema/` for OpenAPI specs
2. **Backend Team**: The staff filtering system maintains historical accuracy - no fallback logic
3. **Database**: Staff records use `date_left` field (null = currently active)

## Summary

The key change is that the timesheet staff API now requires a date parameter for historical accuracy. Most other functionality should work unchanged, but provides enhanced capabilities for historical staff queries.

**Critical Action**: Update all timesheet components to pass the appropriate date parameter when fetching staff lists.
