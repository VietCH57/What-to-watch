const MediaUtils = {
    displayMediaCard: function(container, item) {
        const genres = item.genres && item.genres.length 
            ? `<p class="genres mb-2">${item.genres.join(', ')}</p>` 
            : '';
    
        const isFavorite = Boolean(item.is_favorite);
        const inWatchlist = Boolean(item.in_watchlist);
        
        const rating = item.average_rating ? 
            `<div class="rating mb-2">
                <i class="fas fa-star text-warning"></i>
                <span class="rating-value">${item.average_rating.toFixed(1)}</span>
                ${item.num_votes ? `<span class="text-muted small">(${item.num_votes} votes)</span>` : ''}
             </div>` 
            : '<div class="rating mb-2">No ratings yet</div>';
    
        const cardElement = $(`
            <div class="col-lg-4 col-md-6 col-12">
                <div class="card">
                    <img src="${item.poster_url || '/static/images/no-poster.png'}" 
                         class="card-img-top" 
                         alt="${item.title}"
                         onerror="this.src='/static/images/no-poster.png'">
                    <div class="card-body d-flex flex-column">
                        <div class="content-section flex-grow-1">
                            <h5 class="card-title" title="${item.title}">${item.title}</h5>
                            <div class="media-info">
                                <p class="year mb-2">Year: ${item.year || 'N/A'}</p>
                                ${rating}
                                ${genres}
                                ${item.plot ? `<p class="plot-short">${item.plot.substring(0, 100)}...</p>` : ''}
                            </div>
                        </div>
                        <div class="card-bottom mt-auto">
                            <div class="action-buttons">
                                <button class="btn btn-sm btn-icon add-to-watchlist ${inWatchlist ? 'active' : ''}" 
                                        data-bs-toggle="tooltip" 
                                        title="${inWatchlist ? 'Remove from Watchlist' : 'Add to Watchlist'}"
                                        data-media-id="${item.id}"
                                        data-in-watchlist="${inWatchlist}">
                                    <i class="fas fa-list"></i>
                                </button>
                                <button class="btn btn-sm btn-icon add-to-history" 
                                        data-bs-toggle="tooltip" 
                                        title="Add to History"
                                        data-media-id="${item.id}">
                                    <i class="fas fa-history"></i>
                                </button>
                                <button class="btn btn-sm btn-icon toggle-favorite ${isFavorite ? 'active' : ''}" 
                                        data-bs-toggle="tooltip" 
                                        title="${isFavorite ? 'Remove from Favorites' : 'Add to Favorites'}"
                                        data-media-id="${item.id}"
                                        data-is-favorite="${isFavorite}">
                                    <i class="fa${isFavorite ? 's' : 'r'} fa-heart"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);
    
        container.append(cardElement);

        cardElement.find('.toggle-favorite').on('click', function(e) {
            e.preventDefault();
            MediaUtils.handleToggleFavorite($(this), item.id);
        });
    
        container.append(cardElement);
    
        // Initialize tooltips and hover effect
        cardElement.find('[data-bs-toggle="tooltip"]').tooltip();
        cardElement.find('.card').hover(
            function() { $(this).addClass('shadow-lg'); },
            function() { $(this).removeClass('shadow-lg'); }
        );
    },

    handleAddToHistory: function(mediaId) {
        $.ajax({
            url: '/api/watch-history',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ media_id: mediaId })
        })
        .done(() => MediaUtils.showToast('Added to watch history'))
        .fail(() => MediaUtils.showToast('Error adding to watch history', 'error'));
    },

    handleToggleFavorite: function(button, mediaId) {
        const isFavorite = button.hasClass('active');
        
        // Don't update UI until we get server confirmation
        $.ajax({
            url: '/api/favorites',
            method: isFavorite ? 'DELETE' : 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ 
                item_id: mediaId,
                item_type: 'media'
            }),
            success: function(response) {
                const newState = !isFavorite;
                
                // Update all buttons for this media ID across the page
                $(`.toggle-favorite[data-media-id="${mediaId}"]`).each(function() {
                    const btn = $(this);
                    
                    // Update button state
                    btn.toggleClass('active', newState);
                    
                    // Update icon
                    const icon = btn.find('i');
                    icon.removeClass('fas far').addClass(newState ? 'fas' : 'far');
                    
                    // Update tooltip
                    const tooltipText = newState ? 'Remove from Favorites' : 'Add to Favorites';
                    btn.attr('title', tooltipText);
                    btn.attr('data-bs-original-title', tooltipText);
                    
                    // Update data attribute
                    btn.attr('data-is-favorite', newState);
                    
                    // Refresh tooltip
                    const tooltip = bootstrap.Tooltip.getInstance(btn[0]);
                    if (tooltip) {
                        tooltip.dispose();
                    }
                    new bootstrap.Tooltip(btn[0]);
                });
                
                // Also update any card containers that might show favorite status
                $(`.card[data-media-id="${mediaId}"]`).each(function() {
                    $(this).attr('data-is-favorite', newState);
                });
                
                MediaUtils.showToast(newState ? 'Added to favorites' : 'Removed from favorites');
                
                // Trigger a custom event that other components can listen to
                $(document).trigger('favoriteStatusChanged', {
                    mediaId: mediaId,
                    isFavorite: newState
                });
            },
            error: function(xhr) {
                MediaUtils.showToast('Error updating favorites', 'error');
            }
        });
    },
    
    updateFavoriteButton: function(button, isFavorite) {
        // Dispose of existing tooltip
        const tooltip = bootstrap.Tooltip.getInstance(button[0]);
        if (tooltip) {
            tooltip.dispose();
        }
    
        // Update button state and attributes
        button.toggleClass('active', isFavorite);
        button.attr('data-is-favorite', isFavorite);
        
        // Update icon
        const icon = button.find('i');
        icon.removeClass('fas far').addClass(isFavorite ? 'fas' : 'far');
        
        // Update tooltip title
        const tooltipTitle = isFavorite ? 'Remove from Favorites' : 'Add to Favorites';
        button.attr('title', tooltipTitle);
        button.attr('data-bs-original-title', tooltipTitle);
        
        // Initialize new tooltip
        new bootstrap.Tooltip(button[0]);
    },


    checkFavoriteStatus: function(mediaId) {
        return new Promise((resolve) => {
            $.ajax({
                url: `/api/check-favorite/${mediaId}`,
                method: 'GET',
                success: function(response) {
                    resolve(response.is_favorite);
                },
                error: function() {
                    resolve(false);
                }
            });
        });
    },


    // shared.js (continued)
    handleAddToWatchlist: function(button, mediaId) {
        const inWatchlist = button.hasClass('active');
        $.ajax({
            url: '/api/watchlist',
            method: inWatchlist ? 'DELETE' : 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ media_id: mediaId })
        })
        .done(function() {
            button.toggleClass('active');
            button.attr('title', inWatchlist ? 'Add to Watchlist' : 'Remove from Watchlist');
            MediaUtils.showToast(inWatchlist ? 'Removed from watchlist' : 'Added to watchlist');
        })
        .fail(() => MediaUtils.showToast('Error updating watchlist', 'error'));
    },


    showToast: function(message, type = 'success') {
        const toast = $(`
            <div class="toast-notification ${type}">
                ${message}
            </div>
        `);
        $('body').append(toast);
        setTimeout(() => toast.fadeOut(() => toast.remove()), 3000);
    }
};