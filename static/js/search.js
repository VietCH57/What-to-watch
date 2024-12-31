// static/js/search.js

$(document).ready(function() {
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
                    // Sort suggestions to prioritize exact matches
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
        const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
        
        // Add a class to the ul element for dark mode styling
        $(ul).addClass('ui-autocomplete-custom');
        if (isDarkMode) {
            $(ul).addClass('dark-mode');
        }

        const highlightedTitle = title.replace(
            new RegExp('(' + searchTerm + ')', 'gi'),
            `<strong style="color: ${isDarkMode ? '#007bff' : '#0056b3'}">$1</strong>`
        );

        return $("<li>")
            .append(`<div>${highlightedTitle} (${item.label.split('(')[1]}`)
            .appendTo(ul);
    };

    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.attributeName === "data-theme") {
                const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                $('.ui-autocomplete').toggleClass('dark-mode', isDark);
            }
        });
    });

    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });

    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();

    // Search functionality
    function performSearch() {
        const query = $("#searchInput").val().trim();
        if (query.length < 2) return;

        $("#loadingSpinner").show();
        $("#searchResults").hide();
        $("#noResults").hide();

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

    // Event listeners
    $("#searchButton").click(performSearch);
    $("#searchInput").keypress(function(e) {
        if (e.which === 13) {
            performSearch();
        }
    });
    $("#sortBy").change(performSearch);
    $("#searchType").change(function() {
        $("#sortByContainer").show();
        performSearch();
    });

    // Display search results
    function displayResults(results) {
        const container = $("#searchResults");
        container.empty();
    
        if (!results || !results.length) {
            container.html('<div class="col-12 text-center mt-4">No results found</div>');
            return;
        }
    
        // Create rows of 3 cards each
        for (let i = 0; i < results.length; i += 3) {
            const rowDiv = $('<div class="row mb-4"></div>'); // Add margin-bottom to rows
            container.append(rowDiv);
            
            // Add up to 3 cards in this row
            const rowCards = results.slice(i, i + 3);
            rowCards.forEach(item => displayMediaCard(rowDiv, item));
        }
        
        // Reinitialize tooltips
        $('[data-bs-toggle="tooltip"]').tooltip();
    }

    // Media card display
    function displayMediaCard(container, item) {
        const ratingDisplay = item.average_rating 
            ? `${item.average_rating.toFixed(1)} (${item.num_votes} votes)`
            : 'No ratings';
        
        const genres = item.genres && item.genres.length 
            ? `<p class="genres mb-2">${item.genres.join(', ')}</p>` 
            : '';
    
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
                            <div class="rating-section">
                                <div class="rating">
                                    <i class="fas fa-star text-warning"></i>
                                    <span>${ratingDisplay}</span>
                                </div>
                            </div>
                            <div class="action-buttons">
                                <button class="btn btn-sm btn-icon add-to-history" 
                                        data-bs-toggle="tooltip" 
                                        title="Add to History"
                                        data-media-id="${item.id}">
                                    <i class="fas fa-history"></i>
                                </button>
                                <button class="btn btn-sm btn-icon toggle-favorite ${item.is_favorite ? 'active' : ''}" 
                                        data-bs-toggle="tooltip" 
                                        title="${item.is_favorite ? 'Remove from Favorites' : 'Add to Favorites'}"
                                        data-media-id="${item.id}">
                                    <i class="fa${item.is_favorite ? 's' : 'r'} fa-heart"></i>
                                </button>
                                <button class="btn btn-sm btn-icon add-to-watchlist ${item.in_watchlist ? 'active' : ''}" 
                                        data-bs-toggle="tooltip" 
                                        title="${item.in_watchlist ? 'Remove from Watchlist' : 'Add to Watchlist'}"
                                        data-media-id="${item.id}">
                                    <i class="fas fa-list"></i>
                                </button>
                                <button class="btn btn-sm btn-icon rate-media" 
                                        data-bs-toggle="tooltip" 
                                        title="Rate"
                                        data-media-id="${item.id}">
                                    <i class="fas fa-star"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);
}
    // Action button handlers
    $(document).on('click', '.action-buttons button', function(e) {
        e.preventDefault();
        const mediaId = $(this).data('media-id');
        const button = $(this);

        if (button.hasClass('add-to-history')) {
            handleAddToHistory(mediaId);
        } else if (button.hasClass('toggle-favorite')) {
            handleToggleFavorite(button, mediaId);
        } else if (button.hasClass('add-to-watchlist')) {
            handleAddToWatchlist(button, mediaId);
        } else if (button.hasClass('rate-media')) {
            showRatingModal(mediaId);
        }
    });

    // API handlers
    function handleAddToHistory(mediaId) {
        $.post('/api/watch-history', { media_id: mediaId })
            .done(() => showToast('Added to watch history'))
            .fail(() => showToast('Error adding to watch history', 'error'));
    }

    function handleToggleFavorite(button, mediaId) {
        const isFavorite = button.find('i').hasClass('fas');
        $.ajax({
            url: '/api/favorites',
            method: isFavorite ? 'DELETE' : 'POST',
            data: { media_id: mediaId }
        })
        .done(function() {
            button.find('i').toggleClass('far fas');
            button.toggleClass('active');
            button.attr('title', isFavorite ? 'Add to Favorites' : 'Remove from Favorites');
            showToast(isFavorite ? 'Removed from favorites' : 'Added to favorites');
        })
        .fail(() => showToast('Error updating favorites', 'error'));
    }

    function handleAddToWatchlist(button, mediaId) {
        const inWatchlist = button.hasClass('active');
        $.ajax({
            url: '/api/watchlist',
            method: inWatchlist ? 'DELETE' : 'POST',
            data: { media_id: mediaId }
        })
        .done(function() {
            button.toggleClass('active');
            button.attr('title', inWatchlist ? 'Add to Watchlist' : 'Remove from Watchlist');
            showToast(inWatchlist ? 'Removed from watchlist' : 'Added to watchlist');
        })
        .fail(() => showToast('Error updating watchlist', 'error'));
    }

    // Rating modal
    function showRatingModal(mediaId) {
        // Implement your rating modal here
        const rating = prompt('Rate from 1-10:');
        if (rating && !isNaN(rating) && rating >= 1 && rating <= 10) {
            $.post('/api/update-rating', {
                media_id: mediaId,
                rating: parseFloat(rating)
            })
            .done(() => showToast('Rating updated'))
            .fail(() => showToast('Error updating rating', 'error'));
        }
    }

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