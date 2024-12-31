// recommendations.js
$(document).ready(function() {
    $('[data-bs-toggle="tooltip"]').tooltip();

    function loadRecommendations(refresh = false) {
        $("#loadingSpinner").show();
        $("#recommendationsResults").hide();

        $.ajax({
            url: "/recommendations",
            data: {
                refresh: refresh,
                sort: $("#sortBy").val(),
                page: new URLSearchParams(window.location.search).get('page') || 1
            },
            success: async function(response) {
                await displayResults(response.items);
                updatePagination(response.current_page, response.total_pages);
            },
            error: function() {
                MediaUtils.showToast('Error loading recommendations', 'error');
            },
            complete: function() {
                $("#loadingSpinner").hide();
                $("#recommendationsResults").show();
            }
        });
    }

    function updatePagination(currentPage, totalPages) {
        const pagination = $('.pagination');
        pagination.empty();
        
        for (let i = 1; i <= totalPages; i++) {
            pagination.append(`
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="?page=${i}">${i}</a>
                </li>
            `);
        }
    }

    async function displayResults(results) {
        const container = $("#recommendationsResults");
        container.empty();
    
        if (!results || !results.length) {
            container.html('<div class="col-12 text-center mt-4">No recommendations found</div>');
            return;
        }
    
        // Create individual cards without wrapping in additional row divs
        for (const item of results) {
            if (typeof item.is_favorite !== 'boolean') {
                item.is_favorite = await MediaUtils.checkFavoriteStatus(item.id);
            }
            MediaUtils.displayMediaCard(container, item);
        }
    
        // Initialize tooltips
        $('[data-bs-toggle="tooltip"]').tooltip();
    }

    // Initial load
    loadRecommendations();

    // Event handlers
    $("#refreshRecommendations").click(() => loadRecommendations(true));
    $("#sortBy").change(() => loadRecommendations());

    // Reuse event handlers from shared code
    $(document).on('click', '.add-to-history', function(e) {
        e.preventDefault();
        MediaUtils.handleAddToHistory($(this).data('media-id'));
    });

    $(document).on('click', '.toggle-favorite', function(e) {
        e.preventDefault();
        e.stopPropagation();
        MediaUtils.handleToggleFavorite($(this), $(this).data('media-id'));
    });

    $(document).on('click', '.add-to-watchlist', function(e) {
        e.preventDefault();
        MediaUtils.handleAddToWatchlist($(this), $(this).data('media-id'));
    });
});