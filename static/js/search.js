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
            success: async function(results) {
                await displayResults(results);
            },
            error: function() {
                MediaUtils.showToast('Error performing search', 'error');
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

    // Display results using shared MediaUtils
    async function displayResults(results) {
        const container = $("#searchResults");
        container.empty();
    
        if (!results || !results.length) {
            container.html('<div class="col-12 text-center mt-4">No media found</div>');
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


    // Event handlers using shared MediaUtils
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