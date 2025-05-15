/**
 * Portfolio management functionality for the Investment Dashboard
 */

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    initStockSymbolAutocomplete();
    initDeleteConfirmations();
});

/**
 * Initialize autocomplete for stock symbol inputs
 */
function initStockSymbolAutocomplete() {
    const stockInputs = document.querySelectorAll('.stock-symbol-input');
    
    stockInputs.forEach(input => {
        // Add event listener for input changes
        input.addEventListener('input', debounce(async function() {
            const query = this.value.trim();
            if (query.length < 2) return;
            
            try {
                const response = await fetch(`/stock/search?q=${encodeURIComponent(query)}`);
                if (!response.ok) throw new Error('Search request failed');
                
                const symbols = await response.json();
                showAutocompleteResults(this, symbols);
            } catch (error) {
                console.error('Error searching stocks:', error);
            }
        }, 300));
    });
}

/**
 * Display autocomplete results for stock symbols
 */
function showAutocompleteResults(inputElement, symbols) {
    // Remove any existing dropdown
    let dropdown = inputElement.parentElement.querySelector('.autocomplete-dropdown');
    if (dropdown) dropdown.remove();
    
    // Create dropdown element
    dropdown = document.createElement('div');
    dropdown.className = 'autocomplete-dropdown';
    
    // No results
    if (!symbols || symbols.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'autocomplete-item no-results';
        noResults.textContent = 'No matching symbols found';
        dropdown.appendChild(noResults);
    } else {
        // Add each symbol to dropdown
        symbols.forEach(symbol => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.textContent = symbol;
            item.addEventListener('click', function() {
                inputElement.value = symbol;
                dropdown.remove();
            });
            dropdown.appendChild(item);
        });
    }
    
    // Add dropdown to DOM
    inputElement.parentElement.appendChild(dropdown);
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function closeDropdown(e) {
        if (e.target !== inputElement && e.target !== dropdown) {
            dropdown.remove();
            document.removeEventListener('click', closeDropdown);
        }
    });
}

/**
 * Initialize confirmation dialogs for delete actions
 */
function initDeleteConfirmations() {
    const deleteButtons = document.querySelectorAll('.delete-item-btn');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Debounce function to limit API calls
 */
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

/**
 * Format a number as currency (Indian Rupees)
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2
    }).format(amount);
}

/**
 * Format a number as percentage
 */
function formatPercent(value) {
    return value.toFixed(2) + '%';
}
