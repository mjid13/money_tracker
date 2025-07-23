/**
 * Chart initialization and configuration
 * Requires Chart.js to be loaded
 */

// Store chart instances so we can destroy and recreate them
let chartInstances = {
    incomeExpenseChart: null,
    categoryChart: null,
    trendChart: null,
    balanceChart: null
};

// Initialize dashboard charts
function initDashboardCharts(chartData) {
    // Only proceed if we have chart data
    if (!chartData || Object.keys(chartData).length === 0) {
        console.log('No chart data available');
        return;
    }

    // 1. Income vs Expense Chart
    if (chartData.income_expense && document.getElementById('incomeExpenseChart')) {
        // Destroy existing chart if it exists
        if (chartInstances.incomeExpenseChart) {
            chartInstances.incomeExpenseChart.destroy();
        }
        
        chartInstances.incomeExpenseChart = new Chart(document.getElementById('incomeExpenseChart'), {
            type: 'doughnut',
            data: chartData.income_expense,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // 2. Category Distribution Chart
    if (chartData.category_distribution && document.getElementById('categoryChart')) {
        // Destroy existing chart if it exists
        if (chartInstances.categoryChart) {
            chartInstances.categoryChart.destroy();
        }
        
        chartInstances.categoryChart = new Chart(document.getElementById('categoryChart'), {
            type: 'pie',
            data: chartData.category_distribution,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        display: false
                    }
                }
            }
        });
    }

    // 3. Monthly Trend Chart
    if (chartData.monthly_trend && document.getElementById('trendChart')) {
        // Destroy existing chart if it exists
        if (chartInstances.trendChart) {
            chartInstances.trendChart.destroy();
        }
        
        chartInstances.trendChart = new Chart(document.getElementById('trendChart'), {
            type: 'line',
            data: chartData.monthly_trend,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // 4. Account Balance Chart
    if (chartData.account_balance && document.getElementById('balanceChart')) {
        // Destroy existing chart if it exists
        if (chartInstances.balanceChart) {
            chartInstances.balanceChart.destroy();
        }
        
        chartInstances.balanceChart = new Chart(document.getElementById('balanceChart'), {
            type: 'bar',
            data: chartData.account_balance,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
}

// Function to get current filter values
function getFilterValues() {
    const accountFilter = document.getElementById('chart_account_filter');
    const dateFilter = document.getElementById('chart_date_filter');
    
    return {
        accountNumber: accountFilter ? accountFilter.value : 'all',
        dateRange: dateFilter ? dateFilter.value : 'overall'
    };
}

// Function to fetch chart data based on filters
function fetchChartData(accountNumber, dateRange) {
    // Show loading indicator
    document.querySelectorAll('.chart-container').forEach(container => {
        container.classList.add('loading');
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'chart-loading';
        loadingDiv.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
        container.appendChild(loadingDiv);
    });
    
    // Fetch data from the server
    fetch(`/get_chart_data?account_number=${accountNumber}&date_range=${dateRange}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Remove loading indicators
            document.querySelectorAll('.chart-loading').forEach(el => el.remove());
            document.querySelectorAll('.chart-container').forEach(container => {
                container.classList.remove('loading');
            });
            
            // Update charts with new data
            initDashboardCharts(data);
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
            // Remove loading indicators
            document.querySelectorAll('.chart-loading').forEach(el => el.remove());
            document.querySelectorAll('.chart-container').forEach(container => {
                container.classList.remove('loading');
            });
            
            // Show error message
            const errorMessage = document.createElement('div');
            errorMessage.className = 'alert alert-danger';
            errorMessage.textContent = 'Error loading chart data. Please try again.';
            document.querySelector('.chart-container').parentNode.insertBefore(errorMessage, document.querySelector('.chart-container'));
            
            // Auto-remove error message after 5 seconds
            setTimeout(() => {
                errorMessage.remove();
            }, 5000);
        });
}

// Function to update charts based on current filters
function updateCharts() {
    const filters = getFilterValues();
    fetchChartData(filters.accountNumber, filters.dateRange);
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the dashboard page by looking for chart containers
    const chartContainers = document.querySelectorAll('.chart-container');
    if (chartContainers.length === 0) {
        return; // Not on dashboard page, exit early
    }
    
    // Use the global chart data variable set in the dashboard template
    if (window.chartData) {
        initDashboardCharts(window.chartData);
    } else {
        console.log('No chart data available');
    }
    
    // Add event listener to account filter dropdown
    const accountFilter = document.getElementById('chart_account_filter');
    if (accountFilter) {
        accountFilter.addEventListener('change', updateCharts);
    }
    
    // Add event listener to date range filter dropdown
    const dateFilter = document.getElementById('chart_date_filter');
    if (dateFilter) {
        dateFilter.addEventListener('change', updateCharts);
    }
});