document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const metalTypeFilter = document.getElementById('metalTypeFilter');
    const xeroStatusFilter = document.getElementById('xeroStatusFilter');
    const clearFilters = document.getElementById('clearFilters');
    const mappingCards = document.querySelectorAll('.mapping-card');
    const resultsCount = document.getElementById('resultsCount');

    function highlightSearchTerms(text, searchTerm) {
        if (!searchTerm) return text;
        const regex = new RegExp(`(${searchTerm})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    function filterMappings() {
        const statusValue = statusFilter.value;
        const metalTypeValue = metalTypeFilter.value;
        const xeroStatusValue = xeroStatusFilter.value;
        const searchValue = searchInput.value.toLowerCase().trim();

        let visibleCount = 0;

        mappingCards.forEach(card => {
            let show = true;

            // Status filter
            if (statusValue === 'validated' && card.dataset.validated !== 'true') show = false;
            if (statusValue === 'unvalidated' && card.dataset.validated !== 'false') show = false;

            // Metal type filter
            if (metalTypeValue && card.dataset.metalType !== metalTypeValue) show = false;

            // Xero status filter
            if (xeroStatusValue && card.dataset.xeroStatus !== xeroStatusValue) show = false;

            // Search filter
            if (searchValue) {
                const searchText = card.dataset.searchText.toLowerCase();
                if (!searchText.includes(searchValue)) {
                    show = false;
                } else {
                    // Highlight search terms in visible text
                    const searchableElements = card.querySelectorAll('.searchable-text');
                    searchableElements.forEach(el => {
                        const originalText = el.textContent;
                        el.innerHTML = highlightSearchTerms(originalText, searchValue);
                    });
                }
            } else {
                // Remove highlights when no search
                const searchableElements = card.querySelectorAll('.searchable-text');
                searchableElements.forEach(el => {
                    el.innerHTML = el.textContent;
                });
            }

            card.style.display = show ? 'block' : 'none';
            if (show) visibleCount++;
        });

        // Update results count
        resultsCount.textContent = `Showing ${visibleCount} mappings${searchValue ? ` for "${searchValue}"` : ''}`;
    }

    // Real-time search on input
    searchInput.addEventListener('input', filterMappings);
    statusFilter.addEventListener('change', filterMappings);
    metalTypeFilter.addEventListener('change', filterMappings);
    xeroStatusFilter.addEventListener('change', filterMappings);

    clearFilters.addEventListener('click', function() {
        searchInput.value = '';
        statusFilter.value = '';
        metalTypeFilter.value = '';
        xeroStatusFilter.value = '';
        filterMappings();
        searchInput.focus();
    });

    // Validation functionality
    document.querySelectorAll('.validate-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const mappingId = this.dataset.mappingId;
            const form = document.querySelector(`.mapping-form[data-mapping-id="${mappingId}"]`);
            const formData = new FormData(form);

            // Add CSRF token
            formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

            fetch(`/purchasing/api/product-mapping/${mappingId}/validate/`, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload(); // Refresh to show updated status
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while validating the mapping.');
            });
        });
    });

    // Focus search input on page load
    searchInput.focus();

    // Initial filter application
    filterMappings();
});
