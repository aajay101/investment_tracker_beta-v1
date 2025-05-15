/**
 * Charts for the Investment Dashboard
 * Handles rendering of portfolio performance and other visualizations
 */

// Initialize portfolio performance chart when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializePerformanceChart();
});

/**
 * Initialize the portfolio performance chart using Chart.js
 */
function initializePerformanceChart() {
    const performanceChartElement = document.getElementById('performanceChart');
    if (!performanceChartElement) return;
    
    // Get chart data from data attribute
    let chartData;
    try {
        chartData = JSON.parse(performanceChartElement.dataset.chart);
    } catch (error) {
        console.error('Error parsing chart data:', error);
        return;
    }
    
    // Default data if empty
    if (!chartData || !chartData.dates || chartData.dates.length === 0) {
        chartData = {
            dates: ['No data'],
            values: [0],
            daily_changes: [0]
        };
    }
    
    // Create the performance chart
    const ctx = performanceChartElement.getContext('2d');
    const performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.dates,
            datasets: [{
                label: 'Portfolio Value (₹)',
                data: chartData.values,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 3,
                pointBackgroundColor: 'rgba(54, 162, 235, 1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: 'rgba(255, 255, 255, 0.8)'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `Value: ₹${context.raw.toLocaleString('en-IN', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            })}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)',
                        callback: function(value) {
                            return '₹' + value.toLocaleString('en-IN');
                        }
                    }
                }
            }
        }
    });
    
    // Create the daily change chart if element exists
    const dailyChangeElement = document.getElementById('dailyChangeChart');
    if (dailyChangeElement) {
        const ctxDaily = dailyChangeElement.getContext('2d');
        const dailyChangeChart = new Chart(ctxDaily, {
            type: 'bar',
            data: {
                labels: chartData.dates,
                datasets: [{
                    label: 'Daily Change (%)',
                    data: chartData.daily_changes,
                    backgroundColor: function(context) {
                        const value = context.dataset.data[context.dataIndex];
                        return value >= 0 ? 'rgba(75, 192, 75, 0.7)' : 'rgba(255, 99, 132, 0.7)';
                    },
                    borderColor: function(context) {
                        const value = context.dataset.data[context.dataIndex];
                        return value >= 0 ? 'rgba(75, 192, 75, 1)' : 'rgba(255, 99, 132, 1)';
                    },
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: 'rgba(255, 255, 255, 0.8)'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Change: ${context.raw.toFixed(2)}%`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.7)'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.7)',
                            callback: function(value) {
                                return value.toFixed(2) + '%';
                            }
                        }
                    }
                }
            }
        });
    }
}
