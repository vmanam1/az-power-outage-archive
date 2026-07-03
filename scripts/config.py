APS_URL = "https://aps-ags.esriemcs.com/arcgis/rest/services/APSOutageMap/MapServer/0/query"

APS_PARAMS = {
    "f": "json",
    "outFields": "*",
    "outSR": 4326,
    "returnGeometry": "true",
    "spatialRel": "esriSpatialRelIntersects",
    "where": "(outagestatus = 0) AND (datastatus = 'current')"
}

REQUEST_TIMEOUT = 30

SSVEC_URL = "https://services.arcgis.com/oiVF7alPNKGlpRRF/arcgis/rest/services/Active_Outages_Public/FeatureServer/0/query"

SSVEC_PARAMS = {
    "f": "json",
    "where": "1=1",
    "outFields": "*",
    "outSR": 4326,
    "returnGeometry": "true",
}
