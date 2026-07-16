// Outage Explorer Map Module
let map;
let markersGroup;
let currentOutages = [];

const PROVIDER_COLORS = {
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

const DEFAULT_CENTER = [34.0489, -111.0937]; // Arizona Centroid
const DEFAULT_ZOOM = 7;

function initMap() {
    // Initialize map
    map = L.map('map', {
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
        zoomControl: true
    });

    // Add standard OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Set up marker clustering
    markersGroup = L.markerClusterGroup({
        maxClusterRadius: 40,
        showCoverageOnHover: false,
        spiderfyOnMaxZoom: true
    });
    map.addLayer(markersGroup);

    // Bind center button click
    document.getElementById('reset-map-view-btn').addEventListener('click', (e) => {
        e.preventDefault();
        resetMapView();
    });

    updateLegend();
}

function resetMapView() {
    if (map) {
        map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    }
}

function getMarkerRadius(customers) {
    // Logarithmic scale so 1 customer is small, 10,000+ is large but manageable
    if (!customers || customers <= 0) return 6;
    return Math.min(25, Math.max(6, Math.log10(customers + 1) * 6));
}

function buildPopupHtml(outage) {
    let html = `<div class="popup-title">
        <span class="provider-tag provider-${outage.provider}">${outage.provider}</span>
        Outage Details
    </div>`;
    html += `<table class="popup-table">`;
    
    const fields = [
        { label: 'Customers Affected', val: outage.customers },
        { label: 'Cause', val: outage.cause },
        { label: 'Outage Start', val: outage.start_time },
        { label: 'Estimated Restoration', val: outage.etr },
        { label: 'Restored Time', val: outage.restored_time },
        { label: 'Snapshot Time', val: outage.snapshot_time },
        { label: 'City / Region', val: outage.city },
        { label: 'Boundary Description', val: outage.boundary },
        { label: 'Incident ID', val: outage.incident_id },
        { label: 'Pole Number', val: outage.pole_number },
        { label: 'Event ID', val: outage.event },
        { label: 'Division', val: outage.division },
        { label: 'Customers Restored', val: outage.customers_restored },
        { label: 'Last Updated', val: outage.last_update },
        { label: 'Comments / Status', val: outage.comments },
        { label: 'Coordinates', val: outage.latitude ? `${outage.latitude.toFixed(5)}, ${outage.longitude.toFixed(5)}` : null }
    ];

    fields.forEach(f => {
        if (f.val !== null && f.val !== undefined && f.val !== '') {
            html += `<tr><td class="label">${f.label}</td><td>${f.val}</td></tr>`;
        }
    });
    html += `</table>`;
    return html;
}

function updateMapMarkers(outages) {
    if (!map || !markersGroup) return;

    markersGroup.clearLayers();
    currentOutages = outages;

    const bounds = L.latLngBounds();
    let hasValidPoints = false;

    outages.forEach(outage => {
        if (outage.latitude && outage.longitude) {
            const latLng = [outage.latitude, outage.longitude];
            
            const color = PROVIDER_COLORS[outage.provider] || '#94a3b8';
            const radius = getMarkerRadius(outage.customers);

            const marker = L.circleMarker(latLng, {
                radius: radius,
                fillColor: color,
                color: '#ffffff',
                weight: 1.5,
                opacity: 0.9,
                fillOpacity: 0.75
            });

            // Store outage reference inside the marker layer for table click callbacks
            marker.outageData = outage;

            // Popup
            marker.bindPopup(buildPopupHtml(outage), {
                maxWidth: 320
            });

            markersGroup.addLayer(marker);
            bounds.extend(latLng);
            hasValidPoints = true;
        }
    });

    // Auto-fit to bounds if we have points
    if (hasValidPoints && outages.length > 0) {
        map.fitBounds(bounds, {
            padding: [40, 40],
            maxZoom: 13
        });
    } else {
        resetMapView();
    }

    updateLegend();
}

function updateLegend() {
    const legendItems = document.getElementById('legend-items');
    if (!legendItems) return;

    legendItems.innerHTML = '';
    
    // Get unique providers among current map markers or active providers
    const activeProviders = new Set(currentOutages.map(o => o.provider));
    
    const providersToDisplay = activeProviders.size > 0 ? Array.from(activeProviders) : Object.keys(PROVIDER_COLORS);
    providersToDisplay.sort();

    providersToDisplay.forEach(prov => {
        const color = PROVIDER_COLORS[prov] || '#94a3b8';
        const div = document.createElement('div');
        div.className = 'legend-item';
        div.innerHTML = `
            <span class="legend-color" style="background-color: ${color}"></span>
            <span class="legend-text" style="text-transform: uppercase;">${prov}</span>
        `;
        legendItems.appendChild(div);
    });
}

function zoomToMarker(lat, lng) {
    if (!map || !markersGroup) return;

    // Find marker in cluster group
    let foundLayer = null;
    markersGroup.eachLayer(layer => {
        if (layer.getLatLng && layer.getLatLng().lat === lat && layer.getLatLng().lng === lng) {
            foundLayer = layer;
        }
    });

    if (foundLayer) {
        // Center view on coordinate and zoom in
        map.setView([lat, lng], 14);
        
        // Open popup with short delay to allow map movement
        setTimeout(() => {
            markersGroup.zoomToShowLayer(foundLayer, () => {
                foundLayer.openPopup();
            });
        }, 300);
    }
}
