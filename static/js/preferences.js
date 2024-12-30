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

// Add this to your existing debounce function if it's not already there
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

// Search Functionality
function initializeSearchFunctionality() {
    document.getElementById('minRating').addEventListener('input', function() {
        document.getElementById('minRatingValue').textContent = this.value;
    });
}

async function searchMovies() {
    const query = document.getElementById('movieSearch').value;
    if (!query) return;

    try {
        const response = await fetch(`/api/search/movies?q=${encodeURIComponent(query)}`);
        const media = await response.json();
        
        const resultsDiv = document.getElementById('movieResults');
        resultsDiv.innerHTML = '';
        
        if (media.length === 0) {
            resultsDiv.innerHTML = '<div class="list-group-item">No results found</div>';
            return;
        }
        
        media.forEach(item => {
            const a = document.createElement('a');
            a.className = 'list-group-item list-group-item-action d-flex align-items-center';
            
            let displayText = `${item.title} (${item.year})`;
            if (item.rating) {
                displayText += ` ★${item.rating.toFixed(1)}`;
            }
            
            const icon = item.type === 'tv' ? '📺' : '🎬';
            
            let content = `<div class="me-2">${icon}</div>`;
            if (item.poster_url) {
                content += `<img src="${item.poster_url}" alt="" class="me-2" style="height: 50px;">`;
            }
            content += `<div>${displayText}</div>`;
            
            a.innerHTML = content;
            a.onclick = () => addMovie(item);
            resultsDiv.appendChild(a);
        });
    } catch (error) {
        console.error('Error searching media:', error);
        const resultsDiv = document.getElementById('movieResults');
        resultsDiv.innerHTML = '<div class="list-group-item text-danger">Error searching media</div>';
    }
}

async function searchPeople() {
    const query = document.getElementById('peopleSearch').value;
    if (!query) return;

    try {
        const response = await fetch(`/api/search/people?q=${encodeURIComponent(query)}`);
        const people = await response.json();
        
        const resultsDiv = document.getElementById('peopleResults');
        resultsDiv.innerHTML = '';
        
        people.forEach(person => {
            const a = document.createElement('a');
            a.className = 'list-group-item list-group-item-action';
            a.innerHTML = `${person.name} (${person.roles.join(', ')})`;
            a.onclick = () => addPerson(person);
            resultsDiv.appendChild(a);
        });
    } catch (error) {
        console.error('Error searching people:', error);
    }
}

function addMovie(media) {
    const selectedDiv = document.getElementById('selectedMovies');
    const exists = document.querySelector(`input[name="favorite_movies[]"][value="${media.id}"]`);
    
    if (!exists) {
        saveFavorite(media.id, 'media', 'add')
            .then(() => {
                const badge = createMediaBadge(media);
                selectedDiv.appendChild(badge);
            })
            .catch(error => {
                console.error('Error saving favorite:', error);
                showToast('Error saving favorite', 'error');
            });
    }
    
    document.getElementById('movieSearch').value = '';
    document.getElementById('movieResults').innerHTML = '';
}

function addPerson(person) {
    const selectedDiv = document.getElementById('selectedPeople');
    const exists = document.querySelector(`input[name="favorite_people[]"][value="${person.id}"]`);
    
    if (!exists) {
        saveFavorite(person.id, 'person', 'add')
            .then(() => {
                const badge = createPersonBadge(person);
                selectedDiv.appendChild(badge);
            })
            .catch(error => {
                console.error('Error saving favorite:', error);
                showToast('Error saving favorite', 'error');
            });
    }
    
    document.getElementById('peopleSearch').value = '';
    document.getElementById('peopleResults').innerHTML = '';
}

function createMediaBadge(media) {
    const badge = document.createElement('div');
    badge.className = 'badge bg-primary me-2';
    
    const icon = media.type === 'tv' ? '📺' : '🎬';
    badge.innerHTML = `
        ${icon} ${media.title}
        <input type="hidden" name="favorite_movies[]" value="${media.id}">
        <button type="button" class="btn-close btn-close-white" 
                onclick="removeMovie(this.parentElement, ${media.id})"></button>
    `;
    
    return badge;
}

function createPersonBadge(person) {
    const badge = document.createElement('div');
    badge.className = 'badge bg-success me-2';
    
    badge.innerHTML = `
        ${person.name} (${person.roles.join(', ')})
        <input type="hidden" name="favorite_people[]" value="${person.id}">
        <button type="button" class="btn-close btn-close-white" 
                onclick="removePerson(this.parentElement, ${person.id})"></button>
    `;
    
    return badge;
}

function removeMovie(element, movieId) {
    saveFavorite(movieId, 'media', 'remove')
        .then(() => {
            element.remove();
        })
        .catch(error => {
            console.error('Error removing favorite:', error);
            showToast('Error removing favorite', 'error');
        });
}

function removePerson(element, personId) {
    saveFavorite(personId, 'person', 'remove')
        .then(() => {
            element.remove();
        })
        .catch(error => {
            console.error('Error removing favorite:', error);
            showToast('Error removing favorite', 'error');
        });
}

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