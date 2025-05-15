/**
 * Watchlist functionality for the Investment Dashboard
 */

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    initWatchlistNotes();
    initWatchlistRefresh();
});

/**
 * Initialize notes editing functionality for watchlist items
 */
function initWatchlistNotes() {
    const editButtons = document.querySelectorAll('.edit-notes-btn');
    
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            const notesElement = document.querySelector(`.notes-content[data-item-id="${itemId}"]`);
            const notesFormElement = document.querySelector(`.notes-form[data-item-id="${itemId}"]`);
            
            if (notesElement && notesFormElement) {
                // Toggle visibility
                notesElement.classList.toggle('d-none');
                notesFormElement.classList.toggle('d-none');
                
                // Focus on textarea
                const textarea = notesFormElement.querySelector('textarea');
                if (textarea) {
                    textarea.focus();
                }
            }
        });
    });
    
    // Cancel buttons
    const cancelButtons = document.querySelectorAll('.cancel-notes-btn');
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const itemId = this.dataset.itemId;
            const notesElement = document.querySelector(`.notes-content[data-item-id="${itemId}"]`);
            const notesFormElement = document.querySelector(`.notes-form[data-item-id="${itemId}"]`);
            
            if (notesElement && notesFormElement) {
                // Toggle visibility
                notesElement.classList.toggle('d-none');
                notesFormElement.classList.toggle('d-none');
                
                // Reset form
                const form = notesFormElement.querySelector('form');
                if (form) form.reset();
            }
        });
    });
}

/**
 * Initialize refresh functionality for watchlist prices
 */
function initWatchlistRefresh() {
    const refreshButton = document.getElementById('refresh-watchlist');
    if (!refreshButton) return;
    
    refreshButton.addEventListener('click', async function() {
        this.disabled = true;
        this.innerHTML = '<span class="loading-spinner"></span> Refreshing...';
        
        try {
            await refreshWatchlistPrices();
            this.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Prices';
            showNotification('Prices refreshed successfully!', 'success');
        } catch (error) {
            console.error('Error refreshing prices:', error);
            this.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Failed';
            showNotification('Error refreshing some prices', 'danger');
        } finally {
            this.disabled = false;
        }
    });
    
    // Auto-refresh every 3 minutes for real-time data
    setInterval(refreshWatchlistPrices, 3 * 60 * 1000);
}

/**
 * Show notification at the top of the page
 */
function showNotification(message, type = 'info') {
    // Create notification container if it doesn't exist
    let container = document.querySelector('.notification-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'notification-container position-fixed top-0 start-50 translate-middle-x p-3';
        container.style.zIndex = 1050;
        document.body.appendChild(container);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to container
    container.appendChild(notification);
    
    // Auto dismiss after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Refresh all watchlist prices
 */
async function refreshWatchlistPrices() {
    const watchlistItems = document.querySelectorAll('.watchlist-item');
    
    for (const item of watchlistItems) {
        const symbol = item.dataset.symbol;
        const priceElement = item.querySelector('.current-price');
        const changeElement = item.querySelector('.daily-change');
        
        if (symbol && priceElement) {
            try {
                const response = await fetch(`/stock/price/${encodeURIComponent(symbol)}`);
                if (!response.ok) continue;
                
                const data = await response.json();
                
                // Update price
                if (priceElement) {
                    priceElement.textContent = formatCurrency(data.price);
                }
                
                // Get daily change data
                const [change, changePercent] = await getStockDailyChange(symbol);
                
                // Update change display
                if (changeElement && change !== null && changePercent !== null) {
                    const changeClass = change >= 0 ? 'text-success' : 'text-danger';
                    const changeSign = change >= 0 ? '+' : '';
                    changeElement.textContent = `${changeSign}${change.toFixed(2)} (${changeSign}${changePercent.toFixed(2)}%)`;
                    changeElement.className = `daily-change ${changeClass}`;
                }
                
            } catch (error) {
                console.error(`Error refreshing ${symbol}:`, error);
            }
        }
    }
}

/**
 * Get daily change data for a stock
 */
async function getStockDailyChange(symbol) {
    try {
        const response = await fetch(`/stock/daily-change/${encodeURIComponent(symbol)}`);
        if (!response.ok) return [null, null];
        
        const data = await response.json();
        return [data.change, data.change_percent];
    } catch (error) {
        console.error(`Error getting daily change for ${symbol}:`, error);
        return [null, null];
    }
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
