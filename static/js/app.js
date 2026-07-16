// Outage Explorer App Module
let defaultDateRange = { start_date: '', end_date: '' };
let lastFileCount = 0;
let lastMaxMtime = 0.0;
let pollingInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Leaflet map and Data Table modules
    if (typeof initMap === 'function') initMap();
    if (typeof initTable === 'function') initTable();

    // 2. Setup Dark Mode theme listener
    initTheme();

    // 3. Load initial configuration and metadata
    loadMetadata().then(() => {
        // After metadata loads, read URL parameters and fetch data
        syncFiltersFromUrl();
        fetchData();
        
        // Start background polling for updates
        startPolling();
    });

    // 4. Bind DOM Actions
    setupEventHandlers();
});

function initTheme() {
    const themeToggle = document.getElementById('dark-mode-toggle');
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    } else {
        document.body.classList.remove('dark-theme');
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-theme');
            const currentTheme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';
            localStorage.setItem('theme', currentTheme);
            
            // Re-render table and charts to match theme grid line colors
            if (typeof renderTable === 'function') renderTable();
            // app.js global storage for current datasets
            if (window.latestOutages && window.latestTimeline) {
                if (typeof updateCharts === 'function') updateCharts(window.latestOutages, window.latestTimeline);
            }
        });
    }
}

async function loadMetadata() {
    try {
        const response = await fetch('/api/metadata');
        if (!response.ok) throw new Error('Failed to load metadata');
        const meta = await response.json();

        // 1. Render Provider checklist
        const listContainer = document.getElementById('provider-checkbox-list');
        if (listContainer) {
            listContainer.innerHTML = '';
            meta.providers.forEach(prov => {
                const div = document.createElement('div');
                div.className = 'checkbox-wrapper';
                div.innerHTML = `
                    <label class="checkbox-label">
                        <input type="checkbox" name="providers" value="${prov}" checked>
                        <span style="text-transform: uppercase;">${prov}</span>
                    </label>
                `;
                // Add listener to trigger search chip update
                div.querySelector('input').addEventListener('change', () => {
                    updateFilterChips();
                });
                listContainer.appendChild(div);
            });
        }

        // 2. Set default date range to most recent 10 days present in archive
        if (meta.date_bounds && meta.date_bounds.latest) {
            // Latest is format "2026-07-15 16:08:00 MST"
            const latestStr = meta.date_bounds.latest.split(' ')[0]; // "2026-07-15"
            const latestDate = new Date(latestStr + 'T00:00:00');
            
            const earliestDate = new Date(latestDate.getTime());
            earliestDate.setDate(latestDate.getDate() - 10);
            
            const pad = (n) => String(n).padStart(2, '0');
            
            defaultDateRange.end_date = latestStr;
            defaultDateRange.start_date = `${earliestDate.getFullYear()}-${pad(earliestDate.getMonth()+1)}-${pad(earliestDate.getDate())}`;
        }
        
        // Store boundaries on date pickers as max/min if desired
        if (meta.date_bounds) {
            const startInput = document.getElementById('start_date');
            const endInput = document.getElementById('end_date');
            if (startInput && endInput) {
                const earliestStr = meta.date_bounds.earliest.split(' ')[0];
                const latestStr = meta.date_bounds.latest.split(' ')[0];
                startInput.min = earliestStr;
                startInput.max = latestStr;
                endInput.min = earliestStr;
                endInput.max = latestStr;
            }
        }
    } catch (e) {
        console.error(e);
        showToast('Error', 'Could not fetch archive metadata from server.', 'danger');
    }
}

function syncFiltersFromUrl() {
    const params = new URLSearchParams(window.location.search);
    
    // Display Mode
    const displayMode = params.get('display_mode') || 'latest';
    const displaySelect = document.getElementById('display_mode');
    if (displaySelect) {
        displaySelect.value = displayMode;
        toggleDisplayModeInputs(displayMode);
    }

    // Provider check boxes
    const provsParam = params.get('providers');
    const providerList = provsParam ? provsParam.split(',') : [];
    const checkboxes = document.querySelectorAll('input[name="providers"]');
    checkboxes.forEach(cb => {
        cb.checked = provsParam ? providerList.includes(cb.value) : true;
    });

    // Dates
    const fields = [
        'snapshot_time', 'start_date', 'end_date',
        'time_of_day_start', 'time_of_day_end', 'min_customers', 'max_customers',
        'cause'
    ];
    fields.forEach(f => {
        const el = document.getElementById(f);
        if (el) {
            let val = params.get(f);
            if (!val && (f === 'start_date' || f === 'end_date')) {
                val = defaultDateRange[f];
            }
            el.value = val || '';
        }
    });

    // Booleans
    const activeOnly = document.getElementById('active_only');
    if (activeOnly) {
        activeOnly.checked = params.get('active_only') === 'true';
    }
    const inclUnknown = document.getElementById('include_unknown_customers');
    if (inclUnknown) {
        inclUnknown.checked = params.get('include_unknown_customers') === 'true';
    }

    updateFilterChips();
}

function toggleDisplayModeInputs(mode) {
    const snapGroup = document.getElementById('group-snapshot-time');
    const dateGroup = document.getElementById('group-date-range');
    const modeHelp = document.getElementById('display-mode-help');
    
    if (!snapGroup || !dateGroup) return;

    if (mode === 'latest') {
        snapGroup.style.display = 'none';
        dateGroup.style.display = 'none';
        if (modeHelp) modeHelp.textContent = 'Shows the most recent snapshot for each selected provider.';
    } else if (mode === 'snapshot_at_time') {
        snapGroup.style.display = 'block';
        dateGroup.style.display = 'none';
        if (modeHelp) modeHelp.textContent = 'Shows the snapshot at or immediately before the target time for each provider.';
    } else if (mode === 'historical') {
        snapGroup.style.display = 'none';
        dateGroup.style.display = 'block';
        if (modeHelp) modeHelp.textContent = 'Shows cumulative observations from all snapshots in the date range (records may repeat).';
    } else if (mode === 'unique_outages') {
        snapGroup.style.display = 'none';
        dateGroup.style.display = 'block';
        if (modeHelp) modeHelp.textContent = 'Deduplicates outages in the date range by ID or spatial-temporal fallback.';
    }
}

function getActiveFilterQueryString() {
    const params = new URLSearchParams();
    
    // Providers
    const providers = [];
    document.querySelectorAll('input[name="providers"]:checked').forEach(cb => {
        providers.push(cb.value);
    });
    if (providers.length > 0) {
        params.set('providers', providers.join(','));
    }

    // Other inputs
    const displayMode = document.getElementById('display_mode')?.value || 'latest';
    params.set('display_mode', displayMode);

    if (displayMode === 'snapshot_at_time') {
        const snapTime = document.getElementById('snapshot_time')?.value;
        if (snapTime) params.set('snapshot_time', snapTime);
    } else if (displayMode === 'historical' || displayMode === 'unique_outages') {
        const sd = document.getElementById('start_date')?.value;
        const ed = document.getElementById('end_date')?.value;
        if (sd) params.set('start_date', sd);
        if (ed) params.set('end_date', ed);
    }

    // Filters
    const timeStart = document.getElementById('time_of_day_start')?.value;
    const timeEnd = document.getElementById('time_of_day_end')?.value;
    if (timeStart) params.set('time_of_day_start', timeStart);
    if (timeEnd) params.set('time_of_day_end', timeEnd);

    const minC = document.getElementById('min_customers')?.value;
    const maxC = document.getElementById('max_customers')?.value;
    if (minC) params.set('min_customers', minC);
    if (maxC) params.set('max_customers', maxC);

    const cause = document.getElementById('cause')?.value;
    if (cause) params.set('cause', cause);

    if (document.getElementById('active_only')?.checked) {
        params.set('active_only', 'true');
    }
    if (document.getElementById('include_unknown_customers')?.checked) {
        params.set('include_unknown_customers', 'true');
    }

    return params.toString();
}

async function fetchData() {
    // Show Loading indicator state (cards, tables)
    setLoadingState(true);

    const query = getActiveFilterQueryString();
    
    // Update browser URL query params
    const newUrl = `${window.location.pathname}?${query}`;
    window.history.replaceState({ path: newUrl }, '', newUrl);

    try {
        // Fetch outages and timeline data concurrently
        const [outagesRes, timelineRes] = await Promise.all([
            fetch(`/api/outages?${query}`),
            fetch(`/api/timeline?${query}`)
        ]);

        if (!outagesRes.ok || !timelineRes.ok) {
            throw new Error('Server returned error response');
        }

        const outagesData = await outagesRes.json();
        const timelineData = await timelineRes.json();

        // Save globally so we can refresh on dark theme toggle
        window.latestOutages = outagesData.outages || [];
        window.latestTimeline = timelineData || [];

        // 1. Update Summary metrics cards
        updateSummaryCards(outagesData.summary, outagesData.outages.length);

        // 2. Update Map Markers
        if (typeof updateMapMarkers === 'function') {
            updateMapMarkers(outagesData.outages);
        }

        // 3. Update Charts
        if (typeof updateCharts === 'function') {
            updateCharts(outagesData.outages, timelineData);
        }

        // 4. Update Data Table
        if (typeof updateTableData === 'function') {
            updateTableData(outagesData.outages);
        }

    } catch (e) {
        console.error(e);
        showToast('Query Error', 'Failed to retrieve outage records matching the current filters.', 'danger');
    } finally {
        setLoadingState(false);
    }
}

function setLoadingState(isLoading) {
    const list = ['val-visible-records', 'val-total-customers', 'val-selected-providers', 'val-snapshot-files', 'val-earliest-time', 'val-latest-time', 'val-missing-coords'];
    list.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (isLoading) {
                el.classList.add('text-muted');
            } else {
                el.classList.remove('text-muted');
            }
        }
    });
}

function updateSummaryCards(summary, visibleCount) {
    if (!summary) return;

    document.getElementById('val-visible-records').textContent = visibleCount.toLocaleString();
    document.getElementById('val-total-customers').textContent = summary.total_customers.toLocaleString();
    document.getElementById('val-selected-providers').textContent = summary.provider_count;
    document.getElementById('val-snapshot-files').textContent = summary.snapshot_files_count;
    document.getElementById('val-earliest-time').textContent = summary.earliest_visible_snapshot ? summary.earliest_visible_snapshot.replace(' MST', '') : 'N/A';
    document.getElementById('val-latest-time').textContent = summary.latest_visible_snapshot ? summary.latest_visible_snapshot.replace(' MST', '') : 'N/A';
    document.getElementById('val-missing-coords').textContent = summary.missing_coords_count.toLocaleString();

    // Adjust card-total-customers label based on display mode
    const mode = document.getElementById('display_mode')?.value;
    const label = document.getElementById('label-total-customers');
    if (label) {
        if (mode === 'historical') {
            label.innerHTML = '<strong>Cumulative Observations</strong>';
        } else if (mode === 'unique_outages') {
            label.innerHTML = '<strong>Unique Deduplicated Customers</strong>';
        } else {
            label.innerHTML = '<strong>Current total</strong>';
        }
    }
}

function setupEventHandlers() {
    // Sidebar toggle (collapse/expand)
    const sidebar = document.getElementById('filter-sidebar');
    const collapseBtn = document.getElementById('toggle-sidebar-btn');
    const openBtn = document.getElementById('sidebar-open-btn');

    if (collapseBtn && openBtn && sidebar) {
        collapseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            sidebar.classList.add('collapsed');
            openBtn.style.display = 'block';
        });

        openBtn.addEventListener('click', (e) => {
            e.preventDefault();
            sidebar.classList.remove('collapsed');
            openBtn.style.display = 'none';
        });
    }

    // Display mode change listener
    const displaySelect = document.getElementById('display_mode');
    if (displaySelect) {
        displaySelect.addEventListener('change', (e) => {
            toggleDisplayModeInputs(e.target.value);
            updateFilterChips();
        });
    }

    // Form submit
    const form = document.getElementById('filter-form');
    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            fetchData();
        });
    }

    // Form reset
    const resetBtn = document.getElementById('reset-filters-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Clear URL
            window.history.replaceState({}, '', window.location.pathname);
            
            // Reset to defaults
            const displaySelect = document.getElementById('display_mode');
            if (displaySelect) {
                displaySelect.value = 'latest';
                toggleDisplayModeInputs('latest');
            }

            document.querySelectorAll('input[name="providers"]').forEach(cb => cb.checked = true);
            
            const textFields = ['snapshot_time', 'time_of_day_start', 'time_of_day_end', 'min_customers', 'max_customers', 'cause'];
            textFields.forEach(f => {
                const el = document.getElementById(f);
                if (el) el.value = '';
            });

            document.getElementById('start_date').value = defaultDateRange.start_date;
            document.getElementById('end_date').value = defaultDateRange.end_date;

            document.getElementById('active_only').checked = false;
            document.getElementById('include_unknown_customers').checked = false;

            updateFilterChips();
            fetchData();
            showToast('Filters Reset', 'Display and range variables reset to baseline limits.', 'success');
        });
    }

    // Provider Bulk links
    document.getElementById('prov-select-all')?.addEventListener('click', () => {
        document.querySelectorAll('input[name="providers"]').forEach(cb => cb.checked = true);
        updateFilterChips();
    });
    document.getElementById('prov-clear-all')?.addEventListener('click', () => {
        document.querySelectorAll('input[name="providers"]').forEach(cb => cb.checked = false);
        updateFilterChips();
    });

    // Refresh Data button
    document.getElementById('refresh-data-btn')?.addEventListener('click', (e) => {
        e.preventDefault();
        checkUpdates(true);
    });

    // Chips Clear All
    document.getElementById('clear-all-chips')?.addEventListener('click', () => {
        document.getElementById('reset-filters-btn').click();
    });
}

function updateFilterChips() {
    const chipsBar = document.getElementById('active-chips-bar');
    const container = document.getElementById('chips-container');
    if (!chipsBar || !container) return;

    container.innerHTML = '';
    let hasChips = false;

    const addChip = (label, inputId, clearFn) => {
        hasChips = true;
        const chip = document.createElement('div');
        chip.className = 'chip';
        chip.innerHTML = `
            <span>${label}</span>
            <span class="chip-remove" data-id="${inputId}">&times;</span>
        `;
        chip.querySelector('.chip-remove').addEventListener('click', () => {
            clearFn();
            updateFilterChips();
            fetchData();
        });
        container.appendChild(chip);
    };

    // Mode Chip
    const mode = document.getElementById('display_mode')?.value;
    if (mode && mode !== 'latest') {
        const modeLabels = {
            snapshot_at_time: 'Snapshot At Time',
            historical: 'Historical range',
            unique_outages: 'Deduplicated historical'
        };
        addChip(`Mode: ${modeLabels[mode]}`, 'display_mode', () => {
            const select = document.getElementById('display_mode');
            select.value = 'latest';
            toggleDisplayModeInputs('latest');
        });
    }

    // Providers
    const checked = Array.from(document.querySelectorAll('input[name="providers"]:checked')).map(cb => cb.value);
    const totalCheckboxes = document.querySelectorAll('input[name="providers"]').length;
    if (checked.length < totalCheckboxes && checked.length > 0) {
        addChip(`Providers: ${checked.length} selected`, 'providers', () => {
            document.querySelectorAll('input[name="providers"]').forEach(cb => cb.checked = true);
        });
    } else if (checked.length === 0) {
        addChip('No Providers Selected', 'providers', () => {
            document.querySelectorAll('input[name="providers"]').forEach(cb => cb.checked = true);
        });
    }

    // Date/Time
    if (mode === 'snapshot_at_time') {
        const st = document.getElementById('snapshot_time')?.value;
        if (st) {
            addChip(`Time: ${st.replace('T', ' ')}`, 'snapshot_time', () => {
                document.getElementById('snapshot_time').value = '';
            });
        }
    } else if (mode === 'historical' || mode === 'unique_outages') {
        const sd = document.getElementById('start_date')?.value;
        const ed = document.getElementById('end_date')?.value;
        if (sd && sd !== defaultDateRange.start_date) {
            addChip(`Since: ${sd}`, 'start_date', () => {
                document.getElementById('start_date').value = defaultDateRange.start_date;
            });
        }
        if (ed && ed !== defaultDateRange.end_date) {
            addChip(`Until: ${ed}`, 'end_date', () => {
                document.getElementById('end_date').value = defaultDateRange.end_date;
            });
        }
    }

    // Filters
    const minC = document.getElementById('min_customers')?.value;
    if (minC) {
        addChip(`Customers >= ${minC}`, 'min_customers', () => {
            document.getElementById('min_customers').value = '';
        });
    }
    const maxC = document.getElementById('max_customers')?.value;
    if (maxC) {
        addChip(`Customers <= ${maxC}`, 'max_customers', () => {
            document.getElementById('max_customers').value = '';
        });
    }

    const cause = document.getElementById('cause')?.value;
    if (cause) {
        addChip(`Search: "${cause}"`, 'cause', () => {
            document.getElementById('cause').value = '';
        });
    }

    if (document.getElementById('active_only')?.checked) {
        addChip('Active Outages Only', 'active_only', () => {
            document.getElementById('active_only').checked = false;
        });
    }

    chipsBar.style.display = hasChips ? 'flex' : 'none';
}

function startPolling() {
    const refreshSec = parseInt(document.body.getAttribute('data-refresh-interval')) || 60;
    
    // Clean up if already running
    if (pollingInterval) clearInterval(pollingInterval);

    pollingInterval = setInterval(() => {
        checkUpdates(false);
    }, refreshSec * 1000);
}

async function checkUpdates(isManual = false) {
    try {
        const res = await fetch('/api/file-status');
        if (!res.ok) throw new Error('File status fetch error');
        const status = await res.json();

        const indicator = document.getElementById('last-checked-label');
        if (indicator) {
            const now = new Date();
            const pad = (n) => String(n).padStart(2, '0');
            indicator.textContent = `Last checked: ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
        }

        const isFirstRun = (lastFileCount === 0 && lastMaxMtime === 0.0);

        if (isFirstRun) {
            lastFileCount = status.file_count;
            lastMaxMtime = status.max_mtime;
            if (isManual) {
                fetchData();
                showToast('Archive Checked', 'No changes detected. Dashboard is up to date.', 'success');
            }
            return;
        }

        const hasChanges = (status.file_count !== lastFileCount || status.max_mtime !== lastMaxMtime);
        
        if (hasChanges) {
            lastFileCount = status.file_count;
            lastMaxMtime = status.max_mtime;
            
            // Reload metadata in case new providers were introduced
            await loadMetadata();
            
            // Preserving existing filters, reload outage data
            fetchData();
            
            showToast('New Data Loaded', `Archive updated. ${status.file_count} snapshots total.`, 'success');
        } else {
            if (isManual) {
                showToast('Archive Checked', 'No changes detected. Dashboard is up to date.', 'success');
            }
        }
    } catch (e) {
        console.error(e);
        if (isManual) {
            showToast('Check Failed', 'Could not reach server to query update status.', 'danger');
        }
    }
}

function showToast(title, message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <span class="toast-close">&times;</span>
    `;

    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.remove();
    });

    container.appendChild(toast);

    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}
