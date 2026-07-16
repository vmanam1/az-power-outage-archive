// Outage Explorer Charts Module
let customersChart = null;
let outagesChart = null;
let timelineChart = null;

// Provider Hex Colors mapped from map module
const CHARTS_PROVIDER_COLORS = {
    aps: '#00828a',
    srp: '#00a3e0',
    tep: '#f26a36',
    ues: '#a11f50',
    ssvec: '#6a3d9a',
    trico: '#33a02c',
    ed3: '#b8860b',
    mohave: '#e31a1c',
    navopache: '#ff7f00'
};

function getThemeChartOptions() {
    const isDark = document.body.classList.contains('dark-theme');
    const textColor = isDark ? '#cbd5e1' : '#475569';
    const gridColor = isDark ? '#334155' : '#e2e8f0';

    return {
        textColor,
        gridColor,
        isDark
    };
}

function updateCharts(outages, timelineData) {
    const theme = getThemeChartOptions();
    
    // Group data by provider
    const providerStats = {};
    outages.forEach(out => {
        const prov = out.provider.toLowerCase();
        if (!providerStats[prov]) {
            providerStats[prov] = { customers: 0, count: 0 };
        }
        providerStats[prov].customers += out.customers || 0;
        providerStats[prov].count += 1;
    });

    const providers = Object.keys(providerStats).sort();
    const customerCounts = providers.map(p => providerStats[p].customers);
    const outageCounts = providers.map(p => providerStats[p].count);
    const backgroundColors = providers.map(p => CHARTS_PROVIDER_COLORS[p] || '#94a3b8');

    // 1. Customers Chart (Horizontal Bar Chart)
    const ctxCustomers = document.getElementById('chart-customers').getContext('2d');
    if (customersChart) customersChart.destroy();
    customersChart = new Chart(ctxCustomers, {
        type: 'bar',
        data: {
            labels: providers.map(p => p.toUpperCase()),
            datasets: [{
                label: 'Customers Affected',
                data: customerCounts,
                backgroundColor: backgroundColors,
                borderRadius: 4,
                borderWidth: 0
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (ctx) => `${ctx.raw.toLocaleString()} customers` } }
            },
            scales: {
                x: {
                    grid: { color: theme.gridColor },
                    ticks: { color: theme.textColor, font: { family: 'Inter', size: 10 } }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: theme.textColor, font: { family: 'Inter', size: 10, weight: 'bold' } }
                }
            }
        }
    });

    // 2. Outages Count Chart (Doughnut Chart)
    const ctxOutages = document.getElementById('chart-outages').getContext('2d');
    if (outagesChart) outagesChart.destroy();
    outagesChart = new Chart(ctxOutages, {
        type: 'doughnut',
        data: {
            labels: providers.map(p => p.toUpperCase()),
            datasets: [{
                data: outageCounts,
                backgroundColor: backgroundColors,
                borderWidth: theme.isDark ? 2 : 1,
                borderColor: theme.isDark ? '#1e293b' : '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: theme.textColor,
                        font: { family: 'Inter', size: 10 },
                        boxWidth: 12
                    }
                },
                tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.raw} outages` } }
            },
            cutout: '65%'
        }
    });

    // 3. Timeline Chart (Line Chart over Time)
    const ctxTimeline = document.getElementById('chart-timeline').getContext('2d');
    if (timelineChart) timelineChart.destroy();

    if (!timelineData || timelineData.length === 0) {
        // Draw empty chart state if no data
        return;
    }

    // Aggregate timeline data points by timestamp
    // (since timeline points come from multiple providers, group them by timestamp)
    const aggregatedTimeline = {};
    timelineData.forEach(pt => {
        const ts = pt.timestamp;
        if (!aggregatedTimeline[ts]) {
            aggregatedTimeline[ts] = { outages: 0, customers: 0 };
        }
        aggregatedTimeline[ts].outages += pt.outages_count || 0;
        aggregatedTimeline[ts].customers += pt.customers_affected || 0;
    });

    const timelineTimes = Object.keys(aggregatedTimeline).sort();
    // Parse times for nice display labels (e.g. "07/15 16:07")
    const timeLabels = timelineTimes.map(t => {
        try {
            // "2026-07-15 16:08:00 MST" -> "07/15 16:08"
            const parts = t.split(' ');
            if (parts.length >= 2) {
                const dateParts = parts[0].split('-');
                const timeParts = parts[1].split(':');
                return `${dateParts[1]}/${dateParts[2]} ${timeParts[0]}:${timeParts[1]}`;
            }
        } catch (e) {}
        return t;
    });

    const datasetOutages = timelineTimes.map(t => aggregatedTimeline[t].outages);
    const datasetCustomers = timelineTimes.map(t => aggregatedTimeline[t].customers);

    timelineChart = new Chart(ctxTimeline, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [
                {
                    label: 'Active Outages',
                    data: datasetOutages,
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.05)',
                    yAxisID: 'yOutages',
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: timeLabels.length > 50 ? 0 : 2,
                    fill: true
                },
                {
                    label: 'Customers Affected',
                    data: datasetCustomers,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    yAxisID: 'yCustomers',
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: timeLabels.length > 50 ? 0 : 2,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: theme.textColor,
                        font: { family: 'Inter', size: 10 },
                        boxWidth: 12
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        color: theme.textColor,
                        maxRotation: 45,
                        font: { family: 'Inter', size: 9 },
                        maxTicksLimit: 12
                    }
                },
                yOutages: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: theme.gridColor },
                    ticks: { color: theme.textColor, font: { family: 'Inter', size: 9 } },
                    title: { display: true, text: 'Active Outages', color: theme.textColor, font: { family: 'Inter', size: 10, weight: 'bold' } }
                },
                yCustomers: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: theme.textColor, font: { family: 'Inter', size: 9 } },
                    title: { display: true, text: 'Customers Affected', color: theme.textColor, font: { family: 'Inter', size: 10, weight: 'bold' } }
                }
            }
        }
    });
}
