document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('moviePreferences');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        
        try {
            const response = await fetch('/api/recommendations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            console.log(result);
            // Will handle the results display later
        } catch (error) {
            console.error('Error:', error);
        }
    });


    document.querySelector('.dark-mode-toggle').addEventListener('click', function() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        // Simple theme switch without transitions
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    });
    
    // Initialize theme immediately when page loads
    document.addEventListener('DOMContentLoaded', function() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    });



    function handleLayoutChange() {
        const filterBar = document.querySelector('.filter-bar .row');
        const windowWidth = window.innerWidth;
        
        if (windowWidth <= 1200) {
            filterBar.classList.add('centered-layout');
        } else {
            filterBar.classList.remove('centered-layout');
        }
    }

    // Listen for window resize events
    window.addEventListener('resize', handleLayoutChange);

    // Initial check when page loads
    document.addEventListener('DOMContentLoaded', () => {
        handleLayoutChange();
        
        // Your existing DOMContentLoaded code
        setTimeout(function() {
            document.querySelectorAll('.alert').forEach(function(alert) {
                new bootstrap.Alert(alert).close();
            });
        }, 5000);
    });

    // Update rating filter value display
    document.getElementById('ratingFilter').addEventListener('input', function() {
        document.getElementById('ratingFilterValue').textContent = this.value;
    });

    // Submit form when sort selection changes
    document.querySelector('select[name="sort"]').addEventListener('change', function() {
        document.getElementById('filterForm').submit();
    });

});