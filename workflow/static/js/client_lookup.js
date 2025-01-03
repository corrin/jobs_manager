

document.addEventListener('DOMContentLoaded', function () {
    const clientInput = document.getElementById('client_name');
    const suggestionsContainer = document.getElementById('clientSuggestionsContainer');

    if (!clientInput || !suggestionsContainer) {
        console.error('Client input field or suggestions container not found.');
        return;  // Exit early if these elements are missing
    }

    clientInput.addEventListener('input', function () {
        const query = clientInput.value;
        console.log("Client query event triggered: ", query);

        // Only search when there's a query longer than 2 characters
        if (query.length > 2) {
            fetch(`/api/client-search/?q=${encodeURIComponent(query)}`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok: ' + response.statusText);
                }
                return response.json();
            })
            .then(data => {
                displayClientSuggestions(data.results, query);
            })
            .catch(error => {
                console.error('Error fetching client data:', error);
                suggestionsContainer.innerHTML = ''; // Clear suggestions in case of an error
            });
        } else {
            suggestionsContainer.innerHTML = ''; // Clear suggestions if the query is too short
        }
    });

      // Global click event to close the dropdown
      document.addEventListener('click', function (event) {
        console.log("Global click detected:", event.target);

        const isClickInsideInput = clientInput.contains(event.target);
        const isClickInsideContainer = suggestionsContainer.contains(event.target);

        console.log("Is click inside input?", isClickInsideInput);
        console.log("Is click inside container?", isClickInsideContainer);

        if (!isClickInsideInput && !isClickInsideContainer) {
            console.log("Click outside detected. Hiding suggestions.");
            suggestionsContainer.innerHTML = ''; // Clear suggestions
        }
    });

    // Prevent click inside the suggestions container from propagating
    suggestionsContainer.addEventListener('click', function (event) {
        console.log("Click inside suggestions container.");
        event.stopPropagation(); // Prevents global listener from triggering
    });



    function displayClientSuggestions(clients, query) {
        suggestionsContainer.innerHTML = ''; // Clear previous suggestions

        if (clients.length === 0) {
            const noResultsItem = document.createElement('div');
            noResultsItem.classList.add('suggestion-item');
            noResultsItem.textContent = 'No clients found';
            suggestionsContainer.appendChild(noResultsItem);
        } else {
            clients.forEach(client => {
                const suggestionItem = document.createElement('div');
                suggestionItem.classList.add('suggestion-item');
                suggestionItem.textContent = client.name;
                suggestionItem.dataset.clientId = client.id;

                // Add the event listener within this block to avoid 'undefined' error
                suggestionItem.addEventListener('click', function () {
                    clientInput.value = client.name;
                    document.getElementById('client_id').value = client.id;
                    document.getElementById('client_name').value = client.name;
                    console.log('Client updated: ID:', client.id, ' Name:', client.name);
                    autosaveData();
                    suggestionsContainer.innerHTML = ''; // Clear suggestions after selecting
                });

                suggestionsContainer.appendChild(suggestionItem);
            });
        }

        // Add 'Add new client' option at the end of the list
        const addNewOption = document.createElement('div');
        addNewOption.classList.add('suggestion-item', 'add-new-client');
        addNewOption.textContent = `Add new client "${query}"`;
        addNewOption.addEventListener('click', function () {
            // Open the Add New Client form in a new tab
            const newWindow = window.open(`/client/add/?name=${encodeURIComponent(query)}`, '_blank');

            // Focus on the new tab
            if (newWindow) {
                newWindow.focus();
            }
        });
        suggestionsContainer.appendChild(addNewOption);
    }

    function getCsrfToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }
});
