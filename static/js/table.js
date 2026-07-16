// Outage Explorer Table Module
let tableOutages = [];
let tablePage = 1;
let tablePageSize = 25;
let tableSortColumn = 'customers';
let tableSortDirection = 'desc';

function initTable() {
    // Search input listener
    document.getElementById('table-search').addEventListener('input', () => {
        tablePage = 1; // Reset to page 1 on search
        renderTable();
    });

    // Page size dropdown listener
    document.getElementById('page-size').addEventListener('change', (e) => {
        tablePageSize = parseInt(e.target.value) || 25;
        tablePage = 1;
        renderTable();
    });

    // Sorting headers listeners
    const headers = document.querySelectorAll('#outages-table th.sortable');
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.getAttribute('data-sort');
            if (tableSortColumn === column) {
                // Toggle direction
                tableSortDirection = tableSortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                tableSortColumn = column;
                tableSortDirection = 'desc'; // Default to desc for new columns
            }
            renderTable();
        });
    });

    // CSV Export button trigger
    document.getElementById('export-csv-btn').addEventListener('click', (e) => {
        e.preventDefault();
        // app.js exposes getActiveFilterQueryString
        if (typeof getActiveFilterQueryString === 'function') {
            const query = getActiveFilterQueryString();
            window.location.href = `/api/export.csv?${query}`;
        } else {
            window.location.href = '/api/export.csv';
        }
    });
}

function updateTableData(outages) {
    tableOutages = outages;
    tablePage = 1;
    renderTable();
}

function renderTable() {
    const tableBody = document.getElementById('table-body');
    const tableRecordCount = document.getElementById('table-record-count');
    if (!tableBody) return;

    // 1. Client-side Search filter
    const searchQuery = (document.getElementById('table-search').value || '').trim().toLowerCase();
    let processed = tableOutages;
    if (searchQuery) {
        processed = tableOutages.filter(o => {
            return (o.provider || '').toLowerCase().includes(searchQuery) ||
                   (o.cause || '').toLowerCase().includes(searchQuery) ||
                   (o.comments || '').toLowerCase().includes(searchQuery) ||
                   (o.city || '').toLowerCase().includes(searchQuery) ||
                   (o.boundary || '').toLowerCase().includes(searchQuery);
        });
    }

    tableRecordCount.textContent = `${processed.length} visible`;

    // 2. Client-side Sorting
    if (tableSortColumn) {
        processed.sort((a, b) => {
            let valA = a[tableSortColumn];
            let valB = b[tableSortColumn];

            if (valA === null || valA === undefined) valA = '';
            if (valB === null || valB === undefined) valB = '';

            // Type check sorting logic
            if (tableSortColumn === 'customers' || tableSortColumn === 'latitude' || tableSortColumn === 'longitude') {
                valA = parseFloat(valA) || 0;
                valB = parseFloat(valB) || 0;
            } else {
                valA = String(valA).toLowerCase();
                valB = String(valB).toLowerCase();
            }

            if (valA < valB) return tableSortDirection === 'asc' ? -1 : 1;
            if (valA > valB) return tableSortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }

    // Update Sorting Headers Icons in DOM
    const headers = document.querySelectorAll('#outages-table th.sortable');
    headers.forEach(header => {
        const col = header.getAttribute('data-sort');
        header.classList.remove('sort-asc', 'sort-desc');
        if (col === tableSortColumn) {
            header.classList.add(tableSortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    });

    // 3. Client-side Pagination
    const totalRecords = processed.length;
    const totalPages = Math.ceil(totalRecords / tablePageSize) || 1;
    if (tablePage > totalPages) tablePage = totalPages;

    const startIndex = (tablePage - 1) * tablePageSize;
    const endIndex = Math.min(startIndex + tablePageSize, totalRecords);
    const paginated = processed.slice(startIndex, endIndex);

    // 4. Build Table Rows
    tableBody.innerHTML = '';
    
    if (paginated.length === 0) {
        tableBody.innerHTML = `<tr>
            <td colspan="8" class="text-center text-muted">No visible outage records match filters.</td>
        </tr>`;
        renderPagination(totalPages);
        return;
    }

    paginated.forEach(outage => {
        const tr = document.createElement('tr');
        
        // Determine location display cell
        let locationText = 'N/A';
        if (outage.latitude && outage.longitude) {
            locationText = `${outage.latitude.toFixed(4)}, ${outage.longitude.toFixed(4)}`;
            tr.classList.add('has-coords');
        } else {
            tr.classList.add('no-coords');
        }

        tr.innerHTML = `
            <td><span class="provider-tag provider-${outage.provider}">${outage.provider}</span></td>
            <td class="numeric"><strong>${outage.customers.toLocaleString()}</strong></td>
            <td>${outage.cause || '<span class="text-muted">Unknown</span>'}</td>
            <td>${outage.start_time || '<span class="text-muted">N/A</span>'}</td>
            <td>${outage.etr || '<span class="text-muted">N/A</span>'}</td>
            <td>${outage.city || '<span class="text-muted">N/A</span>'}</td>
            <td>${outage.boundary || '<span class="text-muted">N/A</span>'}</td>
            <td class="numeric">${locationText}</td>
        `;

        // Row Click: zoom to map marker
        tr.addEventListener('click', () => {
            if (outage.latitude && outage.longitude) {
                zoomToMarker(outage.latitude, outage.longitude);
                // Scroll smoothly to map area on mobile
                if (window.innerWidth <= 1024) {
                    document.getElementById('map').scrollIntoView({ behavior: 'smooth' });
                }
            }
        });

        tableBody.appendChild(tr);
    });

    renderPagination(totalPages);
}

function renderPagination(totalPages) {
    const container = document.getElementById('pagination-controls');
    if (!container) return;

    container.innerHTML = '';

    // Previous Button
    const prevBtn = document.createElement('button');
    prevBtn.className = 'pagination-btn';
    prevBtn.textContent = '◀';
    prevBtn.disabled = tablePage === 1;
    prevBtn.addEventListener('click', () => {
        if (tablePage > 1) {
            tablePage--;
            renderTable();
        }
    });
    container.appendChild(prevBtn);

    // Numeric Pages (Limit to showing maximum 5 page buttons)
    const maxButtons = 5;
    let startPage = Math.max(1, tablePage - 2);
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        const btn = document.createElement('button');
        btn.className = `pagination-btn ${tablePage === i ? 'active' : ''}`;
        btn.textContent = i;
        btn.addEventListener('click', () => {
            tablePage = i;
            renderTable();
        });
        container.appendChild(btn);
    }

    // Next Button
    const nextBtn = document.createElement('button');
    nextBtn.className = 'pagination-btn';
    nextBtn.textContent = '▶';
    nextBtn.disabled = tablePage === totalPages;
    nextBtn.addEventListener('click', () => {
        if (tablePage < totalPages) {
            tablePage++;
            renderTable();
        }
    });
    container.appendChild(nextBtn);
}
