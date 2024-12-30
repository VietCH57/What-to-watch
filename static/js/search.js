document.addEventListener('DOMContentLoaded', function() {
    initializeSearchComponents();
});

function initializeSearchComponents() {
    const searchTypeSelect = document.getElementById('searchType');
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const sortTypeSelect = document.getElementById('sortType');

    // Initialize jQuery UI Autocomplete
    $(searchInput).autocomplete({
        source: async function(request, response) {
            const query = request.term;
            const searchType = searchTypeSelect.value;
            try {
                const suggestions = await getSuggestions(query, searchType);
                response(suggestions);
            } catch (error) {
                console.error('Autocomplete error:', error);
                response([]);
            }
        },
        minLength: 2
    });

    searchButton.addEventListener('click', async function() {
        const query = searchInput.value.trim();
        const searchType = searchTypeSelect.value;
        const sortType = sortTypeSelect.value;

        if (query.length < 2) {
            showToast('Please enter at least 2 characters to search', 'warning');
            return;
        }

        try {
            const results = await search(query, searchType, sortType);
            displaySearchResults(results, searchType);
        } catch (error) {
            console.error('Search error:', error);
            showToast('Error performing search', 'error');
        }
    });
}

async function getSuggestions(query, searchType) {
    const response = await fetch(`/api/suggestions?query=${encodeURIComponent(query)}&type=${searchType}`);
    if (!response.ok) throw new Error('Failed to fetch suggestions');
    return response.json();
}

async function search(query, searchType, sortType) {
    const response = await fetch(`/api/search_query?query=${encodeURIComponent(query)}&type=${searchType}&sort=${sortType}`);
    if (!response.ok) throw new Error('Search failed');
    return response.json();
}

function displaySearchResults(results, searchType) {
    const resultsContainer = document.getElementById('searchResults');
    resultsContainer.innerHTML = '';

    if (results.length === 0) {
        resultsContainer.innerHTML = '<div class="p-3 text-muted">No results found</div>';
        return;
    }

    results.forEach(result => {
        const card = document.createElement('div');
        card.className = 'card mb-3 col-md-4';

        if (['movie', 'tv'].includes(searchType)) {
            card.innerHTML = `
                <div class="row no-gutters">
                    <div class="col-md-4">
                        <img src="${result.poster_url}" class="card-img" alt="${result.title}">
                    </div>
                    <div class="col-md-8">
                        <div class="card-body">
                            <h5 class="card-title">${result.title} (${result.year})</h5>
                            <p class="card-text">Rating: ${result.average_rating || 'N/A'}</p>
                            <div class="btn-group" role="group" aria-label="Media actions">
                                <button type="button" class="btn btn-outline-secondary" onclick="addToHistory(${result.id})" title="Add to History"><i class="fas fa-history"></i></button>
                                <button type="button" class="btn btn-outline-secondary" onclick="addToFavorites(${result.id}, 'media')" title="Add to Favorites"><i class="fas fa-heart"></i></button>
                                <button type="button" class="btn btn-outline-secondary" onclick="addToWatchlist(${result.id})" title="Add to Watchlist"><i class="fas fa-list"></i></button>
                                <button type="button" class="btn btn-outline-secondary" onclick="rateMedia(${result.id})" title="Rate"><i class="fas fa-star"></i></button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            card.innerHTML = `
                <div class="row no-gutters">
                    <div class="col-md-4">
                        <img src="${result.photo_url}" class="card-img" alt="${result.name}">
                    </div>
                    <div class="col-md-8">
                        <div class="card-body">
                            <h5 class="card-title">${result.name}</h5>
                            <p class="card-text">${result.primary_profession || ''}</p>
                            <button type="button" class="btn btn-outline-secondary" onclick="addToFavorites(${result.id}, 'person')" title="Add to Favorites"><i class="fas fa-heart"></i></button>
                        </div>
                    </div>
                </div>
            `;
        }

        resultsContainer.appendChild(card);
    });
}

async function addToHistory(mediaId) {
    try {
        const response = await fetch('/api/watch-history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ media_id: mediaId })
        });

        if (!response.ok) throw new Error('Failed to add to history');
        showToast('Added to history', 'success');
    } catch (error) {
        console.error('Error adding to history:', error);
        showToast('Error adding to history', 'error');
    }
}

async function addToFavorites(itemId, itemType) {
    try {
        const response = await fetch('/api/save-favorite', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                item_id: itemId,
                item_type: itemType,
                action: 'add'
            })
        });

        if (!response.ok) throw new Error('Failed to add to favorites');
        showToast('Added to favorites', 'success');
    } catch (error) {
        console.error('Error adding to favorites:', error);
        showToast('Error adding to favorites', 'error');
    }
}

async function addToWatchlist(mediaId) {
    try {
        const response = await fetch('/api/watchlist', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ media_id: mediaId, priority: 1 })
        });

        if (!response.ok) throw new Error('Failed to add to watchlist');
        showToast('Added to watchlist', 'success');
    } catch (error) {
        console.error('Error adding to watchlist:', error);
        showToast('Error adding to watchlist', 'error');
    }
}

async function rateMedia(mediaId) {
    const rating = prompt('Enter your rating (1-10):');
    const ratingValue = parseInt(rating);

    if (isNaN(ratingValue) || ratingValue < 1 || ratingValue > 10) {
        showToast('Invalid rating. Please enter a number between 1 and 10.', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/update-rating', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ media_id: mediaId, rating: ratingValue })
        });

        if (!response.ok) throw new Error('Failed to rate media');
        showToast('Media rated', 'success');
    } catch (error) {
        console.error('Error rating media:', error);
        showToast('Error rating media', 'error');
    }
}

function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : 'success'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}