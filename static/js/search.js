$(document).ready(function() {
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();

    // Autocomplete initialization
    $("#searchInput").autocomplete({
        source: function(request, response) {
            $.ajax({
                url: "/api/suggestions",
                dataType: "json",
                data: {
                    query: request.term,
                    type: $("#searchType").val()
                },
                success: function(data) {
                    data.sort((a, b) => {
                        const aStartsWith = a.value.toLowerCase().startsWith(request.term.toLowerCase());
                        const bStartsWith = b.value.toLowerCase().startsWith(request.term.toLowerCase());
                        if (aStartsWith && !bStartsWith) return -1;
                        if (!aStartsWith && bStartsWith) return 1;
                        return a.value.localeCompare(b.value);
                    });
                    response(data);
                }
            });
        },
        minLength: 2,
        select: function(event, ui) {
            $("#searchInput").val(ui.item.value);
            performSearch();
            return false;
        }
    }).autocomplete("instance")._renderItem = function(ul, item) {
        const searchTerm = this.term.toLowerCase();
        const title = item.value;
        const highlightedTitle = title.replace(
            new RegExp('^(' + searchTerm + ')', 'i'),
            '<strong>$1</strong>'
        );
        return $("<li>")
            .append(`<div>${highlightedTitle} (${item.label.split('(')[1]}`)
            .appendTo(ul);
    };

    // Search functionality
    function performSearch() {
        const query = $("#searchInput").val().trim();
        if (query.length < 2) return;

        $("#loadingSpinner").show();
        $("#searchResults").hide();

        $.ajax({
            url: "/api/search_query",
            data: {
                query: query,
                type: $("#searchType").val(),
                sort: $("#sortBy").val() || 'relevance'
            },
            success: function(results) {
                displayResults(results);
            },
            error: function() {
                showToast('Error performing search', 'error');
            },
            complete: function() {
                $("#loadingSpinner").hide();
                $("#searchResults").show();
            }
        });
    }

    // Event listeners for search
    $("#searchButton").click(performSearch);
    $("#searchInput").keypress(function(e) {
        if (e.which === 13) performSearch();
    });
    $("#sortBy").change(performSearch);
    $("#searchType").change(function() {
        $("#sortByContainer").show();
        performSearch();
    });

    // Display results
    async function displayResults(results) {
        const container = $("#searchResults");
        container.empty();
    
        if (!results || !results.length) {
            container.html('<div class="col-12 text-center mt-4">No results found</div>');
            return;
        }
    
        for (let i = 0; i < results.length; i += 3) {
            const rowDiv = $('<div class="row mb-4"></div>');
            container.append(rowDiv);
            
            // Process each item in the current row
            const rowItems = results.slice(i, i + 3);
            for (const item of rowItems) {
                // Make sure is_favorite is properly set
                if (typeof item.is_favorite !== 'boolean') {
                    item.is_favorite = await checkFavoriteStatus(item.id);
                }
                displayMediaCard(rowDiv, item);
            }
        }
    
        // Reinitialize tooltips for new content
        $('[data-bs-toggle="tooltip"]').tooltip();
    }
    
    // Media card display
    function displayMediaCard(container, item) {
        const genres = item.genres && item.genres.length 
            ? `<p class="genres mb-2">${item.genres.join(', ')}</p>` 
            : '';
    
        // Ensure boolean values for states
        const isFavorite = Boolean(item.is_favorite);
        const inWatchlist = Boolean(item.in_watchlist);
    
        container.append(`
            <div class="col-md-4">
                <div class="card d-flex flex-column h-100">
                    <img src="${item.poster_url || '/static/images/no-poster.png'}" 
                         class="card-img-top" 
                         alt="${item.title}"
                         onerror="this.src='/static/images/no-poster.png'">
                    <div class="card-body d-flex flex-column">
                        <div class="content-section flex-grow-1">
                            <h5 class="card-title" title="${item.title}">${item.title}</h5>
                            <div class="media-info">
                                <p class="year mb-2">Year: ${item.year || 'N/A'}</p>
                                ${genres}
                                ${item.plot ? `<p class="plot-short">${item.plot.substring(0, 100)}...</p>` : ''}
                            </div>
                        </div>
                        <div class="card-bottom mt-auto">
                            <div class="action-buttons">
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
                                <button class="btn btn-sm btn-icon add-to-watchlist ${inWatchlist ? 'active' : ''}" 
                                        data-bs-toggle="tooltip" 
                                        title="${inWatchlist ? 'Remove from Watchlist' : 'Add to Watchlist'}"
                                        data-media-id="${item.id}"
                                        data-in-watchlist="${inWatchlist}">
                                    <i class="fas fa-list"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `);
    
        // Initialize tooltips for the new card
        container.find('[data-bs-toggle="tooltip"]').tooltip();
    
        // Add hover effect for the card
        container.find('.card').hover(
            function() { $(this).addClass('shadow-lg'); },
            function() { $(this).removeClass('shadow-lg'); }
        );
    }

    // Action button handlers
    function handleAddToHistory(mediaId) {
        $.ajax({
            url: '/api/watch-history',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ media_id: mediaId })
        })
        .done(() => showToast('Added to watch history'))
        .fail(() => showToast('Error adding to watch history', 'error'));
    }

    function handleToggleFavorite(button, mediaId) {
        const isFavorite = button.hasClass('active');
        
        // Optimistically update UI before the server response
        updateFavoriteButton(button, !isFavorite);
        
        $.ajax({
            url: '/api/favorites',
            method: isFavorite ? 'DELETE' : 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ 
                item_id: mediaId,
                item_type: 'media'
            }),
            success: function(response) {
                showToast(isFavorite ? 'Removed from favorites' : 'Added to favorites');
                
                // Update all instances of the same media item on the page
                $(`.toggle-favorite[data-media-id="${mediaId}"]`).each(function() {
                    updateFavoriteButton($(this), !isFavorite);
                });
            },
            error: function(xhr) {
                // Revert the button state on error
                updateFavoriteButton(button, isFavorite);
                showToast('Error updating favorites', 'error');
            }
        });
    }
    
    // Helper function to update favorite button state
    function updateFavoriteButton(button, isFavorite) {
        // Toggle active class
        button.toggleClass('active', isFavorite);
        
        // Update the icon
        const icon = button.find('i');
        icon.toggleClass('fas', isFavorite).toggleClass('far', !isFavorite);
        
        // Update tooltip
        button.attr('title', isFavorite ? 'Remove from Favorites' : 'Add to Favorites');
        
        // Update data attribute
        button.attr('data-is-favorite', isFavorite);
        
        // Refresh tooltip
        const tooltip = bootstrap.Tooltip.getInstance(button);
        if (tooltip) {
            tooltip.dispose();
        }
        new bootstrap.Tooltip(button);
    }
    
    // Event handler for favorite button
    $(document).on('click', '.toggle-favorite', function(e) {
        e.preventDefault();
        e.stopPropagation();
        const button = $(this);
        const mediaId = button.data('media-id');
        handleToggleFavorite(button, mediaId);
    });
    
    // Add a function to check favorite status when loading results
    function checkFavoriteStatus(mediaId) {
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
    }

    // Event handler for favorite button
    $(document).on('click', '.toggle-favorite', function(e) {
        e.preventDefault();
        e.stopPropagation();
        handleToggleFavorite($(this), $(this).data('media-id'));
    });

    function handleAddToWatchlist(button, mediaId) {
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
            showToast(inWatchlist ? 'Removed from watchlist' : 'Added to watchlist');
        })
        .fail(() => showToast('Error updating watchlist', 'error'));
    }

    // Button click handlers
    $(document).on('click', '.add-to-history', function(e) {
        e.preventDefault();
        handleAddToHistory($(this).data('media-id'));
    });

    $(document).on('click', '.toggle-favorite', function(e) {
        e.preventDefault();
        handleToggleFavorite($(this), $(this).data('media-id'));
    });

    $(document).on('click', '.add-to-watchlist', function(e) {
        e.preventDefault();
        handleAddToWatchlist($(this), $(this).data('media-id'));
    });

    // Toast notification
    function showToast(message, type = 'success') {
        const toast = $(`
            <div class="toast-notification ${type}">
                ${message}
            </div>
        `);
        $('body').append(toast);
        setTimeout(() => toast.fadeOut(() => toast.remove()), 3000);
    }
});