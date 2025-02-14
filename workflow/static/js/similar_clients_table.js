function initializeSimilarClientsTable() {
    const form = document.getElementById('client-form');
    const nameInput = document.querySelector('input[name="name"]');
    const emailInput = document.querySelector('input[name="email"]');
    const phoneInput = document.querySelector('input[name="phone"]');
    const addressInput = document.querySelector('input[name="address"]');
    const accountCustomerInput = document.querySelector('input[name="is_account_customer"]');
    const submitButton = form.querySelector('button[type="submit"]');
    const similarClientsDiv = document.getElementById('similar-clients');
    const similarClientsList = document.getElementById('similar-clients-list');
    let searchTimeout;
    let selectedClientId = null;

    // Function to search for similar clients
    function searchSimilarClients(query) {
        if (query && query.length >= 3) {
            fetch(`/api/client-search/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    similarClientsList.innerHTML = '';
                    
                    if (data.results.length > 0) {
                        data.results.forEach(client => {
                            const row = document.createElement('tr');
                            row.setAttribute('data-client-id', client.id);
                            row.style.cursor = 'pointer';
                            row.innerHTML = `
                                <td>${client.name}</td>
                                <td>${client.email}</td>
                                <td>${client.phone}</td>
                                <td>${client.address}</td>
                                <td>${client.last_invoice_date}</td>
                                <td>${client.total_spend}</td>
                            `;
                            row.addEventListener('click', () => selectClient(client));
                            similarClientsList.appendChild(row);
                        });
                        similarClientsDiv.style.display = 'block';
                    } else {
                        similarClientsDiv.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Error searching clients:', error);
                    similarClientsDiv.style.display = 'none';
                });
        } else {
            similarClientsDiv.style.display = 'none';
        }
    }

    // Function to update form with client data
    function selectClient(client) {
        nameInput.value = client.name;
        emailInput.value = client.email;
        phoneInput.value = client.phone;
        addressInput.value = client.address;
        accountCustomerInput.checked = client.is_account_customer;
        selectedClientId = client.id;
        submitButton.textContent = 'Select Client';
        
        // Add selected class to the clicked row and remove from others
        const rows = similarClientsList.getElementsByTagName('tr');
        for (let row of rows) {
            row.classList.remove('table-primary');
        }
        const selectedRow = document.querySelector(`tr[data-client-id="${client.id}"]`);
        if (selectedRow) {
            selectedRow.classList.add('table-primary');
        }
    }

    // Handle form submission
    form.addEventListener('submit', function(e) {
        if (selectedClientId) {
            e.preventDefault();
            window.opener.postMessage({
                type: 'CLIENT_SELECTED',
                clientId: selectedClientId,
                clientName: nameInput.value
            }, '*');
            window.close();
        }
    });

    // Handle input changes
    nameInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        selectedClientId = null;
        submitButton.textContent = 'Add Client';
        
        // Add delay to prevent too many requests
        searchTimeout = setTimeout(() => {
            searchSimilarClients(query);
        }, 300); // 300ms delay
    });

    // Check for initial name value and search if present
    const initialName = nameInput.value.trim();
    if (initialName) {
        searchSimilarClients(initialName);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeSimilarClientsTable);