document.addEventListener('DOMContentLoaded', function() {
    // Password Toggle Functionality
    const toggleButtons = document.querySelectorAll('.toggle-password');
    
    toggleButtons.forEach(button => {
        // Set initial state
        button.setAttribute('data-visible', 'false');
        
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const passwordInput = this.previousElementSibling;
            
            // Toggle password visibility
            const isVisible = passwordInput.getAttribute('type') === 'password';
            passwordInput.setAttribute('type', isVisible ? 'text' : 'password');
            
            // Toggle the icon state
            this.setAttribute('data-visible', isVisible);
        });
    });

    // Set initial theme
    const savedTheme = localStorage.getItem('theme') || 
                      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    // Update password toggle colors based on theme
    function updatePasswordToggleColors() {
        const toggleButtons = document.querySelectorAll('.toggle-password');
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        toggleButtons.forEach(button => {
            const paths = button.querySelectorAll('.eye-path, .eye-slash');
            paths.forEach(path => {
                path.style.fill = `var(--text-color)`;
            });
        });
    }

    // Call on page load
    updatePasswordToggleColors();

    // Update colors when theme changes
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'data-theme') {
                updatePasswordToggleColors();
            }
        });
    });

    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });
});