document.addEventListener('DOMContentLoaded', function() {
    initializeGenrePreferences();
    initializeGeneralSettings();
    initializeSettingsAutoSave();
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

    const getRecommendationsBtn = document.getElementById('getRecommendationsBtn');
    if (getRecommendationsBtn) {
        getRecommendationsBtn.addEventListener('click', async function() {
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Generating recommendations...';
            
            try {
                // First save all current preferences
                await saveGeneralSettings();
                
                // Redirect to recommendations page with refresh parameter
                window.location.href = '/recommendations?refresh=true';
            } catch (error) {
                showToast('Error saving preferences', 'error');
                this.disabled = false;
                this.innerHTML = '<i class="fas fa-magic me-2"></i>Get Recommendations';
            }
        });
    }
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
                year_to: yearTo,
                include_watch_history: document.getElementById('includeWatchHistory').checked,
                include_ratings: document.getElementById('includeRatings').checked,
                include_favorites: document.getElementById('includeFavorites').checked
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

// Settings autosave
function initializeSettingsAutoSave() {
    const checkboxes = document.querySelectorAll([
        '#includeWatchHistory',
        '#includeRatings',
        '#includeFavorites'
    ].join(','));
    
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', debounce(async () => {
            try {
                await saveGeneralSettings();
            } catch (error) {
                console.error('Error saving settings:', error);
                showToast('Error saving settings', 'error');
            }
        }, 500));
    });
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