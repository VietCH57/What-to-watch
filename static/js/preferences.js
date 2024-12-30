// Genre Preferences Handling
document.addEventListener('DOMContentLoaded', function() {
    initializeGenrePreferences();
    initializeGeneralSettings();
    initializeSearchFunctionality();
    initializeSettingsAutoSave();
    initializeRecommendationsButton();
});

function initializeGenrePreferences() {
    const genreButtons = document.querySelectorAll('.genre-btn');
    
    genreButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const genreId = this.dataset.genreId;
            const weightSlider = this.parentElement.querySelector('.weight-slider');
            const isActive = this.classList.toggle('active');
            
            // Show/hide weight slider with animation
            weightSlider.classList.toggle('d-none', !isActive);
            if (isActive) {
                // Small delay to ensure d-none is processed first
                setTimeout(() => {
                    weightSlider.classList.add('visible');
                }, 0);
            } else {
                weightSlider.classList.remove('visible');
            }
            
            try {
                await saveGenrePreference(genreId, isActive, weightSlider.value);
                showToast('Preference saved', 'success');
            } catch (error) {
                // Revert the button state if save failed
                this.classList.toggle('active');
                weightSlider.classList.toggle('d-none');
                weightSlider.classList.toggle('visible');
                showToast('Error saving preference', 'error');
            }
        });
    });

    // Initialize sliders
    document.querySelectorAll('.weight-slider').forEach(slider => {
        // Set initial visibility based on active state
        const button = slider.parentElement.querySelector('.genre-btn');
        if (button.classList.contains('active')) {
            slider.classList.remove('d-none');
            slider.classList.add('visible');
        }

        slider.addEventListener('input', async function() {
            const genreId = this.dataset.genreId;
            const button = this.parentElement.querySelector('.genre-btn');
            
            if (button.classList.contains('active')) {
                try {
                    await saveGenrePreference(genreId, true, this.value);
                } catch (error) {
                    showToast('Error saving preference', 'error');
                }
            }
        });
    });
}

async function saveGenrePreference(genreId, checked, weight) {
    const response = await fetch('/api/save-genre-preference', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            genre_id: genreId,
            checked: checked,
            weight: weight
        })
    });
    
    if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to save genre preference');
    }
    
    return response.json();
}


// General Settings 
function initializeGeneralSettings() {
    const minRatingSlider = document.getElementById('minRating');
    const minRatingValue = document.getElementById('minRatingValue');
    const yearFromInput = document.getElementById('yearFrom');
    const yearToInput = document.getElementById('yearTo');
    const yearToError = document.getElementById('yearToError');
    
    // Rating slider
    minRatingSlider.addEventListener('input', function() {
        minRatingValue.textContent = this.value;
    });
    
    // Auto-save on rating change
    minRatingSlider.addEventListener('input', debounce(async () => {
        await saveGeneralSettings();
    }, 300));
    
    // Year validation and auto-save
    yearFromInput.addEventListener('input', debounce(async () => {
        const yearFrom = parseInt(yearFromInput.value);
        const yearTo = parseInt(yearToInput.value);
        
        if (yearFrom < 1900 || yearFrom > 2024) {
            yearFromInput.classList.add('is-invalid');
            return;
        }
        
        yearFromInput.classList.remove('is-invalid');
        
        // Update yearTo validation if needed
        validateYearTo(yearTo, yearFrom);
        
        await saveGeneralSettings();
    }, 300));
    
    yearToInput.addEventListener('input', debounce(async () => {
        const yearFrom = parseInt(yearFromInput.value);
        const yearTo = parseInt(yearToInput.value);
        
        validateYearTo(yearTo, yearFrom);
        
        if (!yearToInput.classList.contains('is-invalid')) {
            await saveGeneralSettings();
        }
    }, 300));
    
    function validateYearTo(yearTo, yearFrom) {
        yearToInput.classList.remove('is-invalid');
        
        if (yearTo < 1900 || yearTo > 2024) {
            yearToError.textContent = 'Year must be between 1900 and 2024';
            yearToInput.classList.add('is-invalid');
            return false;
        }
        
        if (yearTo < yearFrom) {
            yearToError.textContent = 'Must be greater than start year';
            yearToInput.classList.add('is-invalid');
            return false;
        }
        
        return true;
    }
}
async function saveGeneralSettings() {
    try {
        const minRating = parseFloat(document.getElementById('minRating').value);
        const yearFrom = parseInt(document.getElementById('yearFrom').value);
        const yearTo = parseInt(document.getElementById('yearTo').value);

        // Validate inputs before saving
        if (yearFrom < 1900 || yearFrom > 2024 || 
            yearTo < 1900 || yearTo > 2024 || 
            yearTo < yearFrom) {
            showToast('Invalid year range', 'error');
            return;
        }

        const response = await fetch('/api/save-settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                min_rating: minRating,
                year_from: yearFrom,
                year_to: yearTo
            })
        });

        if (!response.ok) {
            throw new Error('Failed to save settings');
        }

        showToast('Settings saved', 'success');
    } catch (error) {
        console.error('Error saving settings:', error);
        showToast('Error saving settings', 'error');
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Add to preferences.js

// Initialize new components
function initializeSearchComponents() {
    initializeAutoComplete('#movieSearch', searchMovies, addToFavorites);
    initializeAutoComplete('#peopleSearch', searchPeople, addToFavorites);
    initializeRatingStars();
    initializeSettingsAutosave();
}

// Autocomplete functionality
function initializeAutoComplete(inputSelector, searchFunction, selectCallback) {
    const input = document.querySelector(inputSelector);
    const resultsContainer = document.querySelector(inputSelector + 'Results');
    let debounceTimeout;
    
    input.addEventListener('input', () => {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(async () => {
            const query = input.value.trim();
            if (query.length < 2) {
                resultsContainer.classList.remove('show');
                return;
            }

            try {
                const results = await searchFunction(query);
                displaySearchResults(results, resultsContainer, selectCallback);
            } catch (error) {
                console.error('Search error:', error);
            }
        }, 300);
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !resultsContainer.contains(e.target)) {
            resultsContainer.classList.remove('show');
        }
    });
}

// Enhanced search functions
async function searchMovies(query) {
    const response = await fetch(`/api/search/media?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error('Search failed');
    return response.json();
}

async function searchPeople(query) {
    const response = await fetch(`/api/search/people?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error('Search failed');
    return response.json();
}

function displaySearchResults(results, container, selectCallback) {
    container.innerHTML = '';
    
    if (results.length === 0) {
        container.innerHTML = '<div class="p-3 text-muted">No results found</div>';
        container.classList.add('show');
        return;
    }

    results.forEach(result => {
        const div = document.createElement('div');
        div.className = 'search-result-item';
        
        if (result.poster_url) {
            div.innerHTML = `<img src="${result.poster_url}" alt="">`;
        }
        
        div.innerHTML += `
            <div class="flex-grow-1">
                <div>${result.title || result.name}</div>
                <small class="text-muted">
                    ${result.year ? `(${result.year})` : ''}
                    ${result.roles ? `- ${result.roles.join(', ')}` : ''}
                </small>
            </div>
        `;
        
        div.addEventListener('click', () => selectCallback(result));
        container.appendChild(div);
    });
    
    container.classList.add('show');
}

// Initialize rating stars functionality
function initializeRatingStars() {
    document.querySelectorAll('.rating-stars').forEach(container => {
        const mediaId = container.dataset.mediaId;
        const stars = container.querySelectorAll('.star');
        
        stars.forEach(star => {
            star.addEventListener('click', async () => {
                const rating = parseInt(star.dataset.rating);
                try {
                    await updateRating(mediaId, rating);
                    updateStarDisplay(container, rating);
                } catch (error) {
                    console.error('Error updating rating:', error);
                    showToast('Error updating rating', 'error');
                }
            });
        });
    });
}

async function updateRating(mediaId, rating) {
    const response = await fetch('/api/update-rating', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ media_id: mediaId, rating: rating })
    });
    
    if (!response.ok) throw new Error('Failed to update rating');
    return response.json();
}

function updateStarDisplay(container, rating) {
    container.querySelectorAll('.star').forEach((star, index) => {
        star.classList.toggle('active', index < rating);
    });
}

// Favorites management
async function addToFavorites(item) {
    const itemType = item.roles ? 'person' : 'media';
    const container = itemType === 'person' ? 
        document.getElementById('selectedPeople') : 
        document.getElementById('selectedMovies');
    
    // Check if already exists
    if (container.querySelector(`input[value="${item.id}"]`)) {
        showToast('Item already in favorites', 'info');
        return;
    }

    try {
        await saveFavorite(item.id, itemType, 'add');
        const badge = createBadge(item, itemType);
        container.appendChild(badge);
        showToast('Added to favorites', 'success');
    } catch (error) {
        console.error('Error adding favorite:', error);
        showToast('Error adding to favorites', 'error');
    }

    // Clear search
    const searchInput = itemType === 'person' ? 
        document.getElementById('peopleSearch') : 
        document.getElementById('movieSearch');
    searchInput.value = '';
    document.querySelector(`#${searchInput.id}Results`).classList.remove('show');
}

function createBadge(item, type) {
    const badge = document.createElement('div');
    badge.className = `badge ${type === 'person' ? 'bg-success' : 'bg-primary'} me-2 mb-2`;
    
    let content = '';
    if (type === 'media') {
        content = `${item.type === 'tv' ? '📺' : '🎬'} ${item.title}`;
    } else {
        content = `${item.name} (${item.roles.join(', ')})`;
    }
    
    badge.innerHTML = `
        ${content}
        <input type="hidden" name="favorite_${type}s[]" value="${item.id}">
        <button type="button" class="btn-close btn-close-white" 
                onclick="removeFromFavorites(this.parentElement, ${item.id}, '${type}')"></button>
    `;
    
    return badge;
}

async function removeFromFavorites(element, itemId, itemType) {
    try {
        await saveFavorite(itemId, itemType, 'remove');
        element.remove();
        showToast('Removed from favorites', 'success');
    } catch (error) {
        console.error('Error removing favorite:', error);
        showToast('Error removing from favorites', 'error');
    }
}

// Watch History management
async function removeFromHistory(mediaId) {
    try {
        const response = await fetch('/api/watch-history', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ media_id: mediaId })
        });
        
        if (!response.ok) throw new Error('Failed to remove from history');
        
        const element = document.querySelector(`.watched-item[data-media-id="${mediaId}"]`);
        if (element) {
            element.remove();
        }
        showToast('Removed from watch history', 'success');
    } catch (error) {
        console.error('Error removing from history:', error);
        showToast('Error removing from history', 'error');
    }
}

// Settings autosave
function initializeSettingsAutosave() {
    const checkboxes = document.querySelectorAll([
        '#includeWatchHistory',
        '#includeRatings',
        '#includeFavorites'
    ].join(','));
    
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', debounce(async () => {
            try {
                await saveSettings({
                    include_watch_history: document.getElementById('includeWatchHistory').checked,
                    include_ratings: document.getElementById('includeRatings').checked,
                    include_favorites: document.getElementById('includeFavorites').checked
                });
                showToast('Settings saved', 'success');
            } catch (error) {
                console.error('Error saving settings:', error);
                showToast('Error saving settings', 'error');
            }
        }, 500));
    });
}

async function saveSettings(settings) {
    const response = await fetch('/api/save-settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
    });
    
    if (!response.ok) throw new Error('Failed to save settings');
    return response.json();
}

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeGenrePreferences();
    initializeGeneralSettings();
    initializeSearchComponents();
    initializeSettingsAutosave();
    initializeRecommendationsButton();
});


// Settings Auto-save
function initializeSettingsAutoSave() {
    const saveSettings = debounce(async () => {
        const minRating = document.getElementById('minRating').value;
        const yearFrom = document.getElementById('year_from').value;
        const yearTo = document.getElementById('year_to').value;
        
        try {
            const response = await fetch('/api/save-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    min_rating: minRating,
                    year_from: yearFrom,
                    year_to: yearTo
                })
            });
            
            if (!response.ok) throw new Error('Failed to save settings');
        } catch (error) {
            console.error('Error saving settings:', error);
            showToast('Error saving settings', 'error');
        }
    }, 500);

    document.getElementById('minRating').addEventListener('change', saveSettings);
    document.getElementById('year_from').addEventListener('change', saveSettings);
    document.getElementById('year_to').addEventListener('change', saveSettings);
}

function initializeRecommendationsButton() {
    document.getElementById('getRecommendationsBtn').addEventListener('click', function() {
        window.location.href = "/recommendations";
    });
}

// API Functions
async function saveGenrePreference(genreId, checked, weight) {
    try {
        const response = await fetch('/api/save-genre-preference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                genre_id: genreId,
                checked: checked,
                weight: weight
            })
        });
        
        if (!response.ok) throw new Error('Failed to save genre preference');
        showToast('Preference saved', 'success');
    } catch (error) {
        console.error('Error saving genre preference:', error);
        showToast('Error saving preference', 'error');
    }
}

async function saveFavorite(itemId, itemType, action) {
    const response = await fetch('/api/save-favorite', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            item_id: itemId,
            item_type: itemType,
            action: action
        })
    });
    
    if (!response.ok) throw new Error('Failed to save favorite');
    return response.json();
}

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
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