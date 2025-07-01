/**
 * Contact Management for Jobs
 * Handles the modal for selecting/creating contacts for jobs
 */

document.addEventListener('DOMContentLoaded', function() {
    const contactModal = document.getElementById('contactModal');
    const existingContactsList = document.getElementById('existing_contacts_list');
    const saveContactBtn = document.getElementById('save_contact_btn');
    const newContactForm = document.getElementById('new_contact_form');

    let selectedContactId = null;
    let currentClientId = null;

    // When modal is shown, load contacts for the current client
    contactModal.addEventListener('show.bs.modal', async function() {
        currentClientId = document.getElementById('client_id').value;
        const clientName = document.getElementById('client_name').value;

        // Update client name in modal
        document.getElementById('modal_client_name').textContent = clientName || 'No client selected';

        // Clear form
        newContactForm.reset();
        selectedContactId = document.getElementById('contact_id').value;

        if (!currentClientId) {
            existingContactsList.innerHTML = '<div class="alert alert-warning">Please select a client first.</div>';
            saveContactBtn.disabled = true;
            return;
        }

        saveContactBtn.disabled = false;

        // Load existing contacts
        await loadClientContacts();
    });

    async function loadClientContacts() {
        try {
            const response = await fetch(`/clients/api/client/${currentClientId}/contacts/`);
            const contacts = await response.json();

            existingContactsList.innerHTML = '';

            if (contacts.length === 0) {
                existingContactsList.innerHTML = '<div class="text-muted">No contacts found for this client.</div>';
            } else {
                contacts.forEach(contact => {
                    const isSelected = contact.id === selectedContactId;
                    const contactItem = document.createElement('div');
                    contactItem.className = `list-group-item list-group-item-action ${isSelected ? 'active' : ''}`;
                    contactItem.innerHTML = `
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">${contact.name}${contact.is_primary ? ' <span class="badge bg-primary">Primary</span>' : ''}</h6>
                                ${contact.position ? `<small class="text-muted">${contact.position}</small><br>` : ''}
                                ${contact.phone ? `<small><i class="bi bi-telephone"></i> ${contact.phone}</small><br>` : ''}
                                ${contact.email ? `<small><i class="bi bi-envelope"></i> ${contact.email}</small>` : ''}
                            </div>
                            <div>
                                <button class="btn btn-sm btn-outline-primary select-contact" data-contact-id="${contact.id}" data-contact-name="${contact.name}" data-contact-phone="${contact.phone || ''}">
                                    ${isSelected ? 'Selected' : 'Select'}
                                </button>
                            </div>
                        </div>
                    `;
                    existingContactsList.appendChild(contactItem);
                });
            }

            // Add click handlers for select buttons
            document.querySelectorAll('.select-contact').forEach(btn => {
                btn.addEventListener('click', function() {
                    selectedContactId = this.dataset.contactId;

                    // Update UI to show selection
                    document.querySelectorAll('.list-group-item').forEach(item => {
                        item.classList.remove('active');
                    });
                    this.closest('.list-group-item').classList.add('active');
                    this.textContent = 'Selected';

                    // Update other buttons
                    document.querySelectorAll('.select-contact').forEach(otherBtn => {
                        if (otherBtn !== this) {
                            otherBtn.textContent = 'Select';
                        }
                    });
                });
            });

        } catch (error) {
            console.error('Error loading contacts:', error);
            existingContactsList.innerHTML = '<div class="alert alert-danger">Error loading contacts.</div>';
        }
    }

    // Save contact handler
    saveContactBtn.addEventListener('click', async function() {
        // Check if we're creating a new contact or selecting existing
        const newContactName = document.getElementById('new_contact_name').value.trim();

        if (newContactName) {
            // Create new contact
            const contactData = {
                client: currentClientId,
                name: newContactName,
                position: document.getElementById('new_contact_position').value.trim(),
                email: document.getElementById('new_contact_email').value.trim(),
                phone: document.getElementById('new_contact_phone').value.trim(),
                notes: document.getElementById('new_contact_notes').value.trim(),
                is_primary: document.getElementById('new_contact_primary').checked
            };

            try {
                const response = await fetch('/clients/api/client/contact/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(contactData)
                });

                if (!response.ok) {
                    throw new Error('Failed to create contact');
                }

                const newContact = await response.json();
                selectedContactId = newContact.id;

                // Update the job with the new contact
                updateJobContact(newContact.id, newContact.name, newContact.phone);

                // Close modal
                bootstrap.Modal.getInstance(contactModal).hide();

            } catch (error) {
                console.error('Error creating contact:', error);
                alert('Error creating contact. Please try again.');
            }
        } else if (selectedContactId) {
            // Use selected existing contact
            const selectedBtn = document.querySelector(`.select-contact[data-contact-id="${selectedContactId}"]`);
            if (selectedBtn) {
                const contactName = selectedBtn.dataset.contactName;
                const contactPhone = selectedBtn.dataset.contactPhone;
                updateJobContact(selectedContactId, contactName, contactPhone);
            }

            // Close modal
            bootstrap.Modal.getInstance(contactModal).hide();
        } else {
            alert('Please select an existing contact or create a new one.');
        }
    });

    function updateJobContact(contactId, contactName, contactPhone) {
        // Update hidden field
        document.getElementById('contact_id').value = contactId;

        // Update display field
        const displayValue = contactPhone ? `${contactName} - ${contactPhone}` : contactName;
        document.getElementById('contact_display').value = displayValue;

        // Trigger autosave for contact_id
        const event = new Event('change', { bubbles: true });
        document.getElementById('contact_id').dispatchEvent(event);

        // Update legacy fields (for backward compatibility)
        document.getElementById('contact_person').value = contactName;
        document.getElementById('contact_phone').value = contactPhone || '';
    }

    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
