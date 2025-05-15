/**
 * Dashboard functionality for the Investment Dashboard
 */

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    setupTabPersistence();
});

/**
 * Setup persistence for dashboard tabs
 * This remembers which tab was active between page reloads
 */
function setupTabPersistence() {
    // Check if we have tabs
    const dashboardTabs = document.getElementById('dashboardTabs');
    if (!dashboardTabs) return;
    
    // Get all tab triggers
    const tabTriggers = dashboardTabs.querySelectorAll('[data-bs-toggle="tab"]');
    
    // Set up event listener for tab changes
    tabTriggers.forEach(trigger => {
        trigger.addEventListener('shown.bs.tab', function(event) {
            // Save the active tab ID to localStorage
            localStorage.setItem('activeInvestmentDashboardTab', event.target.id);
        });
    });
    
    // Restore active tab if saved
    const savedTab = localStorage.getItem('activeInvestmentDashboardTab');
    if (savedTab) {
        const tabToActivate = document.getElementById(savedTab);
        if (tabToActivate) {
            const tab = new bootstrap.Tab(tabToActivate);
            tab.show();
        }
    }
}

/**
 * Format numbers for display
 */
const formatters = {
    /**
     * Format a number as currency (Indian Rupees)
     */
    currency: function(amount) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 2
        }).format(amount);
    },
    
    /**
     * Format a number as percentage
     */
    percent: function(value) {
        return value.toFixed(2) + '%';
    },
    
    /**
     * Format a date string (YYYY-MM-DD) to localized format
     */
    date: function(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString();
    }
};

/**
 * Check if an element is in the viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}
