// Outage Explorer Charts Module
let customersChart = null;
let outagesChart = null;
let timelineChart = null;
let causeChart = null;
let statusChart = null;
let hourChart = null;

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
    const textColor = isDark ? '#a2a6b3' : '#5c5f6a';
    const gridColor = isDark ? '#262833' : '#e4e5e9';

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
                borderColor: theme.isDark ? '#17181f' : '#ffffff'
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

    // 3. Top Causes (Horizontal Bar) -- magnitude across cause categories.
    // Single hue: one measure (count), so no legend; the title names it.
    // Providers spell the same cause differently ("WEATHER", "Weather",
    // "Storm/Weather"), so group case-insensitively and fold any
    // weather/storm variant into one "Weather" bucket.
    const canonicalCause = (raw) => {
        const label = (raw || '').trim();
        if (!label) return 'Unknown';
        if (/weather|storm/i.test(label)) return 'Weather';
        // Tame ALL-CAPS spellings; keep mixed-case labels as published.
        if (label === label.toUpperCase()) {
            return label.charAt(0) + label.slice(1).toLowerCase();
        }
        return label;
    };
    const causeCounts = {};
    outages.forEach(out => {
        const label = canonicalCause(out.cause);
        const key = label.toLowerCase();
        if (!causeCounts[key]) causeCounts[key] = { label, count: 0 };
        causeCounts[key].count += 1;
    });
    let causeEntries = Object.values(causeCounts)
        .map(e => [e.label, e.count])
        .sort((a, b) => b[1] - a[1]);
    const CAUSE_TOP_N = 7;
    if (causeEntries.length > CAUSE_TOP_N) {
        const top = causeEntries.slice(0, CAUSE_TOP_N);
        const otherTotal = causeEntries
            .slice(CAUSE_TOP_N)
            .reduce((sum, e) => sum + e[1], 0);
        top.push(['Other', otherTotal]);
        causeEntries = top;
    }
    const ctxCause = document.getElementById('chart-cause').getContext('2d');
    if (causeChart) causeChart.destroy();
    causeChart = new Chart(ctxCause, {
        type: 'bar',
        data: {
            labels: causeEntries.map(e => e[0]),
            datasets: [{
                label: 'Outages',
                data: causeEntries.map(e => e[1]),
                backgroundColor: '#2563eb',
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
                tooltip: { callbacks: { label: (ctx) => ` ${ctx.raw} outage${ctx.raw === 1 ? '' : 's'}` } }
            },
            scales: {
                x: {
                    grid: { color: theme.gridColor },
                    ticks: { color: theme.textColor, font: { family: 'Inter', size: 10 }, precision: 0 }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: theme.textColor, font: { family: 'Inter', size: 10 } }
                }
            }
        }
    });

    // 4. Active vs. Restored (Doughnut) -- status split. Identity carried by the
    // legend labels, never colour alone.
    let activeCount = 0;
    let restoredCount = 0;
    outages.forEach(out => {
        if (out.restored_time) {
            restoredCount += 1;
        } else {
            activeCount += 1;
        }
    });
    const ctxStatus = document.getElementById('chart-status').getContext('2d');
    if (statusChart) statusChart.destroy();
    statusChart = new Chart(ctxStatus, {
        type: 'doughnut',
        data: {
            labels: ['Active', 'Restored'],
            datasets: [{
                data: [activeCount, restoredCount],
                backgroundColor: ['#f59e0b', '#10b981'],
                borderWidth: theme.isDark ? 2 : 1,
                borderColor: theme.isDark ? '#17181f' : '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: theme.textColor, font: { family: 'Inter', size: 10 }, boxWidth: 12 }
                },
                tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.raw.toLocaleString()}` } }
            },
            cutout: '65%'
        }
    });

    // 5. Outage Starts by Hour of Day (Bar) -- distribution across 0-23h.
    const hourBuckets = new Array(24).fill(0);
    outages.forEach(out => {
        const st = out.start_time;
        if (typeof st === 'string') {
            const parts = st.split(' ');
            if (parts.length >= 2) {
                const hh = parseInt(parts[1].split(':')[0], 10);
                if (!isNaN(hh) && hh >= 0 && hh < 24) hourBuckets[hh] += 1;
            }
        }
    });
    const ctxHour = document.getElementById('chart-hour').getContext('2d');
    if (hourChart) hourChart.destroy();
    hourChart = new Chart(ctxHour, {
        type: 'bar',
        data: {
            labels: Array.from({ length: 24 }, (_, h) => String(h).padStart(2, '0')),
            datasets: [{
                label: 'Outage starts',
                data: hourBuckets,
                backgroundColor: '#0ea5e9',
                borderRadius: 3,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: (items) => `Hour ${items[0].label}:00`,
                        label: (ctx) => ` ${ctx.raw} start${ctx.raw === 1 ? '' : 's'}`
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: theme.textColor, font: { family: 'Inter', size: 8 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 12 }
                },
                y: {
                    grid: { color: theme.gridColor },
                    ticks: { color: theme.textColor, font: { family: 'Inter', size: 9 }, precision: 0 }
                }
            }
        }
    });

    // 6. Timeline Chart (Line Chart over Time)
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
