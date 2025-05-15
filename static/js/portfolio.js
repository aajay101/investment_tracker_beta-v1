/**
 * Portfolio management functionality for the Investment Dashboard
 */

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    initStockSymbolAutocomplete();
    initDeleteConfirmations();
    initEditFunctionality();
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
            e.preventDefault();
            const form = this.closest('form');
            const symbol = this.closest('tr').querySelector('td:first-child').textContent.trim();
            
            // Create a more attractive confirmation dialog
            const confirmModal = document.createElement('div');
            confirmModal.className = 'modal fade';
            confirmModal.id = 'deleteConfirmModal';
            confirmModal.setAttribute('tabindex', '-1');
            confirmModal.setAttribute('aria-labelledby', 'deleteConfirmModalLabel');
            confirmModal.setAttribute('aria-hidden', 'true');
            
            confirmModal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-danger text-white">
                            <h5 class="modal-title" id="deleteConfirmModalLabel">Confirm Deletion</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <p>Are you sure you want to delete <strong>${symbol}</strong> from your portfolio?</p>
                            <p class="text-danger"><small>This action cannot be undone.</small></p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger" id="confirmDelete">Delete</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(confirmModal);
            
            // Initialize and show the modal
            const modal = new bootstrap.Modal(confirmModal);
            modal.show();
            
            // Handle confirmation
            document.getElementById('confirmDelete').addEventListener('click', function() {
                form.submit();
            });
            
            // Remove modal from DOM after it's hidden
            confirmModal.addEventListener('hidden.bs.modal', function() {
                confirmModal.remove();
            });
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

/**
 * Initialize the edit form functionality
 */
function initEditFunctionality() {
    // For the edit form, add validations and improvements
    const editForm = document.querySelector('.edit-portfolio-form');
    if (!editForm) return;
    
    // Validate form before submission
    editForm.addEventListener('submit', function(e) {
        // Get form inputs
        const quantity = parseFloat(document.getElementById('quantity').value);
        const buyPrice = parseFloat(document.getElementById('buy_price').value);
        
        let isValid = true;
        let errorMessages = [];
        
        // Validate quantity
        if (isNaN(quantity) || quantity <= 0) {
            isValid = false;
            errorMessages.push('Quantity must be a positive number');
        }
        
        // Validate buy price
        if (isNaN(buyPrice) || buyPrice <= 0) {
            isValid = false;
            errorMessages.push('Buy price must be a positive number');
        }
        
        // Display errors or submit
        if (!isValid) {
            e.preventDefault();
            
            // Create alert for errors
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger';
            alertDiv.innerHTML = '<ul class="mb-0">' + 
                errorMessages.map(msg => `<li>${msg}</li>`).join('') + 
                '</ul>';
            
            // Show alert at top of form
            const formElements = editForm.querySelector('.card-body');
            formElements.insertBefore(alertDiv, formElements.firstChild);
            
            // Scroll to top of form
            window.scrollTo(0, 0);
        }
    });
}
