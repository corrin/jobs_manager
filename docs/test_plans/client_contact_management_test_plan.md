# Test Plan: Client Contact Management Feature

## Overview
This test plan covers the new client contact management system that replaces Xero contact syncing with local contact storage.

## Prerequisites
- [ ] Ensure migrations have been applied (`python manage.py migrate`)
- [ ] Have at least one client in the system
- [ ] Have access to create and edit jobs

## Test Cases

### 1. View Existing Contact Data
- [ ] Navigate to an existing job that previously had contact_person/contact_phone data
- [ ] Verify the contact information is displayed in the read-only field
- [ ] Verify format is "Name - Phone" or just "Name" if no phone

### 2. Open Contact Management Modal
- [ ] Click the "Manage" button next to Contact Person field
- [ ] Verify modal opens with:
  - [ ] Client name displayed at top
  - [ ] List of existing contacts (if any)
  - [ ] Form to add new contact

### 3. Create New Contact
- [ ] In the modal, fill in the new contact form:
  - Name: "John Smith" (required)
  - Position: "Project Manager" (optional)
  - Email: "john@example.com" (optional)
  - Phone: "555-1234" (optional)
  - Notes: "Primary contact for all orders" (optional)
  - Check "Set as primary contact"
- [ ] Click "Save Contact"
- [ ] Verify modal closes
- [ ] Verify contact display updates to "John Smith - 555-1234"
- [ ] Verify hidden contact_id field is populated
- [ ] Verify autosave triggers (check network tab or console)

### 4. Select Existing Contact
- [ ] Open modal again
- [ ] Verify "John Smith" appears in the existing contacts list with "Primary" badge
- [ ] Add another contact "Jane Doe" without marking as primary
- [ ] Close and reopen modal
- [ ] Click "Select" button next to "Jane Doe"
- [ ] Click "Save Contact"
- [ ] Verify contact display updates to "Jane Doe"

### 5. Contact Without Client
- [ ] Create a new job or use one without a client selected
- [ ] Click "Manage" contact button
- [ ] Verify modal shows warning: "Please select a client first."
- [ ] Verify Save button is disabled

### 6. Primary Contact Behavior
- [ ] For a client with multiple contacts, mark a different one as primary
- [ ] Verify only one contact can be primary at a time
- [ ] Verify primary contacts appear first in the list

### 7. Autosave Integration
- [ ] Select/create a contact for a job
- [ ] Make another change to the job (e.g., change job name)
- [ ] Verify both changes are saved
- [ ] Refresh the page
- [ ] Verify contact selection persists

### 8. API Testing (Developer Console)
- [ ] Test fetching contacts:
```javascript
// Replace [CLIENT_ID] with actual client UUID
fetch('/clients/api/client/[CLIENT_ID]/contacts/')
  .then(r => r.json())
  .then(console.log)
```

- [ ] Test creating contact:
```javascript
// Replace [CLIENT_ID] with actual client UUID
fetch('/clients/api/client/contact/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
  },
  body: JSON.stringify({
    client: '[CLIENT_ID]',
    name: 'Test Contact',
    email: 'test@example.com',
    phone: '555-5555',
    is_primary: false
  })
}).then(r => r.json()).then(console.log)
```

### 9. Edge Cases
- [ ] Try to save without selecting any contact (should close modal without changes)
- [ ] Create contact with only name (minimum required field)
- [ ] Create contact with very long name/phone/email
- [ ] Try special characters in contact fields

### 10. Legacy Data Compatibility
- [ ] Find a job with old contact_person/contact_phone data
- [ ] Verify it displays correctly
- [ ] Select a new contact from modal
- [ ] Verify old fields are updated in background (check hidden fields)

### 11. Multiple Browser Testing
- [ ] Test in Chrome
- [ ] Test in Firefox
- [ ] Test in Safari (if available)
- [ ] Test in Edge

### 12. Performance Testing
- [ ] Test with a client that has 50+ contacts
- [ ] Verify modal loads quickly
- [ ] Verify contact list is scrollable and responsive

## Expected Results
- All contact data is stored locally in ClientContact model
- No API calls to Xero for contact management
- Smooth user experience with modal interface
- Backward compatibility with legacy contact fields
- Primary contact designation works correctly

## Known Limitations
- Contact email is not currently displayed in the selection (only name and phone)
- No search/filter functionality in contact list yet
- No bulk import of contacts

## Rollback Plan
If critical issues are found:
1. The migration can be reversed: `python manage.py migrate job 0015`
2. Legacy contact_person and contact_phone fields are preserved
3. The modal can be hidden by removing the "Manage" button from template

## Sign-off
- [ ] Developer testing complete
- [ ] User acceptance testing complete
- [ ] Ready for production deployment

---
*Test Plan Created: 2025-06-09*
*Feature: Client Contact Management*
*Version: 1.0*
