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

// Track ongoing requests to prevent race conditions
let pendingRequests = {
    allCharts: false,
    categoryChart: false
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

    // 2. Category Distribution Chart with built-in filter
    if (chartData.category_distribution && document.getElementById('categoryChart')) {
        // Create filter buttons if they don't exist
        createCategoryFilter();

        // Only update category chart if there's no pending category-specific request
        if (!pendingRequests.categoryChart) {
            updateCategoryChartInstance(chartData);
        }
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

// Helper function to update category chart instance
function updateCategoryChartInstance(chartData) {
    // Destroy existing chart if it exists
    if (chartInstances.categoryChart) {
        chartInstances.categoryChart.destroy();
    }

    // Get category type from radio inputs (new toggle) or old button structure (fallback)
    const radioInput = document.querySelector('input[name="category-filter"]:checked');
    const oldButton = document.querySelector('.category-filter-btn.active');

    let categoryType = 'expense'; // default
    if (radioInput) {
        categoryType = radioInput.value;
    } else if (oldButton) {
        categoryType = oldButton.dataset.filter;
    }

    // Determine which data to use based on filter
    let categoryData;
    if (categoryType === 'income' && chartData.income_categories) {
        categoryData = chartData.income_categories;
    } else if (categoryType === 'expense' && chartData.expense_categories) {
        categoryData = chartData.expense_categories;
    } else {
        categoryData = chartData.category_distribution;
    }

    chartInstances.categoryChart = new Chart(document.getElementById('categoryChart'), {
        type: 'pie',
        data: categoryData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 5,
                    bottom: 60,
                    left: 10,
                    right: 10
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    display: true,
                    align: 'center',
                    maxWidth: 400,
                    fullSize: true,
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 10,
                        boxWidth: 10,
                        boxHeight: 10,
                        font: {
                            size: 11,
                            family: 'system-ui, -apple-system, sans-serif',
                            weight: '500'
                        },
                        color: '#495057',
                        generateLabels: function(chart) {
                            const data = chart.data;
                            if (data.labels.length && data.datasets.length) {
                                const dataset = data.datasets[0];
                                return data.labels.map((label, i) => {
                                    const value = dataset.data[i];
                                    const total = dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);

                                    // Truncate long labels
                                    let displayLabel = label;
                                    if (label.length > 15) {
                                        displayLabel = label.substring(0, 12) + '...';
                                    }

                                    return {
                                        text: `${displayLabel} (${percentage}%)`,
                                        fillStyle: dataset.backgroundColor[i],
                                        strokeStyle: dataset.borderColor ? dataset.borderColor[i] : dataset.backgroundColor[i],
                                        lineWidth: dataset.borderWidth || 0,
                                        pointStyle: 'circle',
                                        hidden: chart.getDatasetMeta(0).data[i].hidden,
                                        index: i
                                    };
                                });
                            }
                            return [];
                        }
                    },
                    onClick: function(e, legendItem, legend) {
                        const index = legendItem.index;
                        const chart = legend.chart;
                        const meta = chart.getDatasetMeta(0);

                        meta.data[index].hidden = !meta.data[index].hidden;
                        chart.update('active');
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    cornerRadius: 8,
                    displayColors: true,
                    padding: 12,
                    titleFont: {
                        size: 13,
                        weight: '600'
                    },
                    bodyFont: {
                        size: 12
                    },
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return [`Amount: ${value}`, `Percentage: ${percentage}%`];
                        }
                    }
                }
            },
            elements: {
                arc: {
                    borderWidth: 2,
                    borderColor: '#fff',
                    hoverBorderWidth: 3,
                    hoverBorderColor: '#fff'
                }
            },
            interaction: {
                intersect: false,
                mode: 'point'
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 800,
                easing: 'easeOutCubic'
            }
        }
    });
}

// Function to create category filter buttons
// Function to create category filter buttons
function createCategoryFilter() {
    const categoryChartContainer = document.getElementById('categoryChart').closest('.chart-container');

    // Check if filter already exists
    if (categoryChartContainer.querySelector('.category-chart-filter')) {
        return;
    }

    // Create filter container with enhanced styling
    const filterContainer = document.createElement('div');
    filterContainer.className = 'category-chart-filter d-flex justify-content-center mb-1';
    filterContainer.innerHTML = `
        <div class="filter-toggle-container">
            <div class="filter-toggle-wrapper">
                <input type="radio" id="expense-filter" name="category-filter" value="expense" checked>
                <input type="radio" id="income-filter" name="category-filter" value="income">
                
                <div class="filter-toggle-track">
                    <div class="filter-toggle-slider">
                        <div class="slider-icon">
                            <div class="butter-icon expense-icon">
                                <div class="icon-circle">
                                    <div class="arrow-down"></div>
                                </div>
                            </div>
                            <div class="butter-icon income-icon">
                                <div class="icon-circle">
                                    <div class="arrow-up"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <label for="expense-filter" class="filter-toggle-label" data-filter="expense">
                        <div class="label-icon expense-label">
                            <div class="icon-ring">
                                <div class="minus-line"></div>
                            </div>
                        </div>
                    </label>
                    <label for="income-filter" class="filter-toggle-label" data-filter="income">
                        <div class="label-icon income-label">
                            <div class="icon-ring">
                                <div class="plus-lines">
                                    <div class="plus-horizontal"></div>
                                    <div class="plus-vertical"></div>
                                </div>
                            </div>
                        </div>
                    </label>
                </div>
            </div>
        </div>
        
        <style>
            .category-chart-filter {
                margin: 0 0 20px 0;
                padding: 0;
                position: relative;
                z-index: 10;
                display: flex;
                align-items: center;
            }

            .filter-toggle-container {
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
                padding: 8px 0;
            }
            
            .filter-toggle-wrapper {
                position: relative;
                background: var(--bs-body-bg, #fff);
                border-radius: 20px;
                padding: 1px;
                box-shadow: 
                    0 4px 20px rgba(0, 0, 0, 0.08),
                    inset 0 1px 0 rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(0, 0, 0, 0.08);
                transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
                backdrop-filter: blur(10px);
            }
            
            .filter-toggle-wrapper:hover {
                box-shadow: 
                    0 6px 25px rgba(0, 0, 0, 0.12),
                    inset 0 1px 0 rgba(255, 255, 255, 0.8);
                transform: translateY(-1px);
            }
            
            .filter-toggle-track {
                position: relative;
                display: flex;
                border-radius: 17px;
                overflow: hidden;
                background: rgba(0, 0, 0, 0.02);
            }

            .filter-toggle-slider {
                position: absolute;
                top: 0;
                left: 0;
                width: 50%;
                height: 100%;
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 50%, #dc3545 100%);
                border-radius: 17px;
                transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
                box-shadow: 
                    0 3px 12px rgba(220, 53, 69, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
                z-index: 2;
                display: flex;
                align-items: center;
                justify-content: center;
                transform-origin: center;
            }
            
            .slider-icon {
                position: relative;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            /* Butter Icon Styles */
            .butter-icon {
                position: absolute;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
            }

            .icon-circle {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.25);
                display: flex;
                align-items: center;
                justify-content: center;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.4);
                box-shadow: 
                    0 1px 4px rgba(0, 0, 0, 0.08),
                    inset 0 1px 0 rgba(255, 255, 255, 0.5);
                transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            }

            .arrow-down, .arrow-up {
                width: 0;
                height: 0;
                transition: all 0.3s ease;
            }

            .arrow-down {
                border-left: 2.5px solid transparent;
                border-right: 2.5px solid transparent;
                border-top: 4px solid white;
                filter: drop-shadow(0 0.5px 1px rgba(0, 0, 0, 0.2));
            }

            .arrow-up {
                border-left: 2.5px solid transparent;
                border-right: 2.5px solid transparent;
                border-bottom: 4px solid white;
                filter: drop-shadow(0 0.5px 1px rgba(0, 0, 0, 0.2));
            }

            .expense-icon {
                opacity: 1;
                transform: scale(1) rotate(0deg);
            }

            .income-icon {
                opacity: 0;
                transform: scale(0.7) rotate(-180deg);
            }

            /* Label Icons */
            .filter-toggle-label {
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                width: 44px;
                height: 44px;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                z-index: 1;
                border-radius: 5px;
                user-select: none;
            }

            .filter-toggle-label:hover {
                transform: scale(1.05);
            }

            .label-icon {
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            }

            .icon-ring {
                width: 16px;
                height: 16px;
                border-radius: 50%;
                border: 1.5px solid rgba(108, 117, 125, 0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                background: rgba(108, 117, 125, 0.05);
            }

            .filter-toggle-label:hover .icon-ring {
                border-color: rgba(108, 117, 125, 0.5);
                background: rgba(108, 117, 125, 0.1);
                transform: rotate(5deg);
            }

            .minus-line {
                width: 6px;
                height: 1.5px;
                background: rgba(108, 117, 125, 0.7);
                border-radius: 1px;
                transition: all 0.3s ease;
            }

            .plus-lines {
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .plus-horizontal, .plus-vertical {
                background: rgba(108, 117, 125, 0.6);
                border-radius: 1px;
                position: absolute;
                transition: all 0.3s ease;
            }

            .plus-horizontal {
                width: 8px;
                height: 2px;
            }

            .plus-vertical {
                width: 2px;
                height: 8px;
            }

            .filter-toggle-label:hover .minus-line,
            .filter-toggle-label:hover .plus-horizontal,
            .filter-toggle-label:hover .plus-vertical {
                background: rgba(108, 117, 125, 0.8);
            }

            input[type="radio"] {
                display: none;
            }

            /* Default state - Expense selected */
            #expense-filter:checked ~ .filter-toggle-track .filter-toggle-slider {
                transform: translateX(0%) scale(1.02);
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 50%, #dc3545 100%);
            }

            #expense-filter:checked ~ .filter-toggle-track .expense-icon {
                opacity: 1;
                transform: scale(1) rotate(0deg);
            }

            #expense-filter:checked ~ .filter-toggle-track .expense-icon .icon-circle {
                background: rgba(255, 255, 255, 0.3);
                transform: scale(1) rotate(0deg);
                box-shadow: 
                    0 3px 12px rgba(255, 255, 255, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.5);
            }

            #expense-filter:checked ~ .filter-toggle-track .income-icon {
                opacity: 0;
                transform: scale(0.6) rotate(-270deg);
            }

            /* Income selected state */
            #income-filter:checked ~ .filter-toggle-track .filter-toggle-slider {
                transform: translateX(100%) scale(1.02);
                background: linear-gradient(135deg, #51cf66 0%, #40c057 50%, #28a745 100%);
                box-shadow: 
                    0 3px 12px rgba(40, 167, 69, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
            }

            #income-filter:checked ~ .filter-toggle-track .expense-icon {
                opacity: 0;
                transform: scale(0.6) rotate(270deg);
            }

            #income-filter:checked ~ .filter-toggle-track .income-icon {
                opacity: 1;
                transform: scale(1) rotate(0deg);
            }

            #income-filter:checked ~ .filter-toggle-track .income-icon .icon-circle {
                background: rgba(255, 255, 255, 0.3);
                transform: scale(1) rotate(0deg);
                box-shadow: 
                    0 3px 12px rgba(255, 255, 255, 0.2),
                    inset 0 1px 0 rgba(255, 255, 255, 0.5);
            }

            /* Hover effects for icons */
            .butter-icon:hover .icon-circle {
                transform: scale(1.1) rotate(10deg);
                background: rgba(255, 255, 255, 0.4);
            }

            /* Micro animations on state change */
            .filter-toggle-slider:hover .icon-circle {
                animation: iconPulse 0.6s cubic-bezier(0.4, 0, 0.6, 1);
            }

            @keyframes iconPulse {
                0% { transform: scale(1) rotate(0deg); }
                50% { transform: scale(1.15) rotate(5deg); }
                100% { transform: scale(1) rotate(0deg); }
            }
   
            @keyframes smoothSpin {
                0% { transform: rotate(0deg) scale(1); }
                50% { transform: rotate(180deg) scale(1.1); }
                100% { transform: rotate(360deg) scale(1); }
            }
            
            /* Active state micro-animation */
            .filter-toggle-wrapper.active {
                transform: scale(0.98);
            }
            
            /* Hover glow effect */
            .filter-toggle-slider::before {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                background: inherit;
                border-radius: 19px;
                filter: blur(8px);
                opacity: 0.3;
                z-index: -1;
                transition: opacity 0.3s ease;
            }
            
            .filter-toggle-wrapper:hover .filter-toggle-slider::before {
                opacity: 0.5;
            }
            
            @media (prefers-reduced-motion: reduce) {
                .filter-toggle-slider,
                .filter-toggle-label,
                .filter-toggle-wrapper,
                .slider-icon i {
                    transition: none !important;
                }
                
            
            }
            
            /* Optimize chart canvas positioning */
            .category-chart-filter + canvas,
            .category-chart-filter ~ canvas,
            .category-chart-filter + div canvas {
                margin-top: 2px !important;
            }

            /* Fix any potential z-index issues */
            #categoryChart {
                position: relative;
                z-index: 1;
            }

            /* Smooth container transitions */
            .chart-container {
                transition: all 0.3s ease;
                padding-top: 0 !important;
            }

            .chart-container.loading {
                pointer-events: none;
            }

            /* Maximize chart area */
            .chart-container canvas {
                max-height: none !important;
            }

            @media (max-width: 576px) {
                .category-chart-filter {
                    margin-bottom: 15px;
                }

                .filter-toggle-wrapper {
                    padding: 2px;
                }
                
                .filter-toggle-label {
                    width: 38px;
                    height: 38px;
                    font-size: 14px;
                }
                
                .slider-icon i {
                    font-size: 10px;
                }
            }
        </style>
    `;

    // Find the exact description element and position toggle inline
    const chartElement = document.getElementById('categoryChart');
    const chartContainer = chartElement.closest('.chart-container');

    // Look for all possible description elements
    const possibleDescriptions = chartContainer.querySelectorAll('p, small, .text-muted, .chart-subtitle');
    let chartDescription = null;

    // Find the description that contains "Distribution" or "expenses" or similar text
    for (let elem of possibleDescriptions) {
        const text = elem.textContent.toLowerCase();
        if (text.includes('distribution') || text.includes('expenses') || text.includes('income') || text.includes('category')) {
            chartDescription = elem;
            break;
        }
    }

    // If still not found, try to find by position (usually the first p or small element)
    if (!chartDescription) {
        chartDescription = chartContainer.querySelector('p, small');
    }

    if (chartDescription) {
        console.log('Found description element:', chartDescription);

        // Store original text and classes
        const originalText = chartDescription.textContent.trim();
        const originalClasses = chartDescription.className;

        // Transform the element into a flex container
        chartDescription.innerHTML = `
            <span class="description-text" style="flex-grow: 1;">${originalText}</span>
            <div class="toggle-container-inline" style="flex-shrink: 0; margin-left: 12px;"></div>
        `;

        // Apply flex styling
        chartDescription.style.cssText = `
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            margin-bottom: 1rem !important;
        `;

        // Add the toggle to the inline container
        const inlineContainer = chartDescription.querySelector('.toggle-container-inline');
        inlineContainer.appendChild(filterContainer);

    } else {
        console.log('Description not found, using fallback positioning');
        // Fallback: add above chart
        const fallbackDiv = document.createElement('div');
        fallbackDiv.style.cssText = 'display: flex; justify-content: flex-end; margin-bottom: 1rem;';
        fallbackDiv.appendChild(filterContainer);
        chartElement.parentNode.insertBefore(fallbackDiv, chartElement);
    }

    // Add event listeners to radio inputs
    const radioInputs = filterContainer.querySelectorAll('input[type="radio"]');
    const wrapper = filterContainer.querySelector('.filter-toggle-wrapper');

    radioInputs.forEach(radio => {
        radio.addEventListener('change', function() {
            // Prevent multiple simultaneous requests
            if (pendingRequests.categoryChart || pendingRequests.allCharts) {
                return;
            }

            // Add active state with bounce effect
            wrapper.classList.add('active');

            setTimeout(() => {
                wrapper.classList.remove('active');
            }, 200);

            // Update chart after a brief delay for smooth animation
            setTimeout(() => {
                updateCategoryChart();
            }, 150);
        });
    });

    // Override the updateCategoryChart function to handle loading state
    const originalUpdateCategoryChart = updateCategoryChart;
    updateCategoryChart = function() {

        // Call original function
        const result = originalUpdateCategoryChart.apply(this, arguments);

        return result;
    };
}
// Function to update only the category chart based on its filter
function updateCategoryChart() {
    // Prevent race conditions
    if (pendingRequests.categoryChart || pendingRequests.allCharts) {
        console.log('Request already in progress, skipping category chart update');
        return;
    }

    // Get category type from radio inputs (new toggle) or old button structure (fallback)
    const radioInput = document.querySelector('input[name="category-filter"]:checked');
    const oldButton = document.querySelector('.category-filter-btn.active');

    let categoryType = 'expense'; // default
    if (radioInput) {
        categoryType = radioInput.value;
    } else if (oldButton) {
        categoryType = oldButton.dataset.filter;
    }

    // Get current global filter values
    const filters = getFilterValues();

    // Fetch data specifically for category chart
    fetchCategoryChartData(filters.accountNumber, filters.dateRange, categoryType);
}

// Function to fetch data specifically for category chart
function fetchCategoryChartData(accountNumber, dateRange, categoryType) {
    // Prevent multiple simultaneous requests
    if (pendingRequests.categoryChart || pendingRequests.allCharts) {
        console.log('Category chart request already in progress');
        return;
    }

    pendingRequests.categoryChart = true;

    const categoryChartContainer = document.getElementById('categoryChart').closest('.chart-container');

    // Show loading indicator only for category chart
    showLoadingForContainer(categoryChartContainer);

    // Fetch data from the server
    fetch(`/api/get_category_chart_data?account_number=${accountNumber}&date_range=${dateRange}&category_type=${categoryType}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Remove loading indicator
            hideLoadingForContainer(categoryChartContainer);

            // Update only the category chart
            if (chartInstances.categoryChart) {
                chartInstances.categoryChart.destroy();
            }

            chartInstances.categoryChart = new Chart(document.getElementById('categoryChart'), {
                type: 'pie',
                data: data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {
                        padding: {
                            top: 5,
                            bottom: 60,
                            left: 10,
                            right: 10
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            display: true,
                            align: 'center',
                            maxWidth: 400,
                            fullSize: true,
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'circle',
                                padding: 10,
                                boxWidth: 10,
                                boxHeight: 10,
                                font: {
                                    size: 10,
                                    family: 'system-ui, -apple-system, sans-serif',
                                    weight: '500'
                                },
                                color: '#495057',
                                generateLabels: function(chart) {
                                    const data = chart.data;
                                    if (data.labels.length && data.datasets.length) {
                                        const dataset = data.datasets[0];
                                        return data.labels.map((label, i) => {
                                            const value = dataset.data[i];
                                            const total = dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = ((value / total) * 100).toFixed(1);

                                            // Truncate long labels
                                            let displayLabel = label;
                                            if (label.length > 15) {
                                                displayLabel = label.substring(0, 12) + '...';
                                            }

                                            return {
                                                text: `${displayLabel} (${percentage}%)`,
                                                fillStyle: dataset.backgroundColor[i],
                                                strokeStyle: dataset.borderColor ? dataset.borderColor[i] : dataset.backgroundColor[i],
                                                lineWidth: dataset.borderWidth || 0,
                                                pointStyle: 'circle',
                                                hidden: chart.getDatasetMeta(0).data[i].hidden,
                                                index: i
                                            };
                                        });
                                    }
                                    return [];
                                }
                            },
                            onClick: function(e, legendItem, legend) {
                                const index = legendItem.index;
                                const chart = legend.chart;
                                const meta = chart.getDatasetMeta(0);

                                meta.data[index].hidden = !meta.data[index].hidden;
                                chart.update('active');
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#fff',
                            bodyColor: '#fff',
                            cornerRadius: 8,
                            displayColors: true,
                            padding: 12,
                            titleFont: {
                                size: 13,
                                weight: '600'
                            },
                            bodyFont: {
                                size: 12
                            },
                            callbacks: {
                                title: function(context) {
                                    return context[0].label;
                                },
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return [`Amount: ${value}`, `Percentage: ${percentage}%`];
                                }
                            }
                        }
                    },
                    elements: {
                        arc: {
                            borderWidth: 2,
                            borderColor: '#fff',
                            hoverBorderWidth: 3,
                            hoverBorderColor: '#fff'
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'point'
                    },
                    animation: {
                        animateRotate: true,
                        animateScale: true,
                        duration: 800,
                        easing: 'easeOutCubic'
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching category chart data:', error);
            hideLoadingForContainer(categoryChartContainer);
            showErrorForContainer(categoryChartContainer, 'Error loading category data. Please try again.');
        })
        .finally(() => {
            pendingRequests.categoryChart = false;
        });
}

// Helper function to show loading for a specific container
function showLoadingForContainer(container) {
    container.classList.add('loading');

    // Remove existing loading indicator first
    const existingLoader = container.querySelector('.chart-loading');
    if (existingLoader) {
        existingLoader.remove();
    }

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chart-loading';
    loadingDiv.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
    container.appendChild(loadingDiv);
}

// Helper function to hide loading for a specific container
function hideLoadingForContainer(container) {
    const loadingElement = container.querySelector('.chart-loading');
    if (loadingElement) {
        loadingElement.remove();
    }
    container.classList.remove('loading');
}

// Helper function to show error for a specific container
function showErrorForContainer(container, message) {
    const errorMessage = document.createElement('div');
    errorMessage.className = 'alert alert-danger alert-sm mt-2';
    errorMessage.textContent = message;
    container.appendChild(errorMessage);

    // Auto-remove error message after 3 seconds
    setTimeout(() => {
        if (errorMessage.parentNode) {
            errorMessage.remove();
        }
    }, 3000);
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
    // Prevent multiple simultaneous requests
    if (pendingRequests.allCharts) {
        console.log('All charts request already in progress');
        return;
    }

    // Cancel any pending category chart request
    pendingRequests.categoryChart = false;
    pendingRequests.allCharts = true;

    // Show loading indicator
    document.querySelectorAll('.chart-container').forEach(container => {
        showLoadingForContainer(container);
    });

    // Fetch data from the server
    fetch(`/api/get_chart_data?account_number=${accountNumber}&date_range=${dateRange}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Remove loading indicators
            document.querySelectorAll('.chart-container').forEach(container => {
                hideLoadingForContainer(container);
            });

            // Update charts with new data
            initDashboardCharts(data);
        })
        .catch(error => {
            console.error('Error fetching chart data:', error);
            // Remove loading indicators
            document.querySelectorAll('.chart-container').forEach(container => {
                hideLoadingForContainer(container);
            });

            // Show error message
            const errorMessage = document.createElement('div');
            errorMessage.className = 'alert alert-danger';
            errorMessage.textContent = 'Error loading chart data. Please try again.';
            const firstContainer = document.querySelector('.chart-container');
            if (firstContainer) {
                firstContainer.parentNode.insertBefore(errorMessage, firstContainer);

                // Auto-remove error message after 5 seconds
                setTimeout(() => {
                    if (errorMessage.parentNode) {
                        errorMessage.remove();
                    }
                }, 5000);
            }
        })
        .finally(() => {
            pendingRequests.allCharts = false;
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