APS_URL = "https://aps-ags.esriemcs.com/arcgis/rest/services/APSOutageMap/MapServer/0/query"

APS_PARAMS = {
    "f": "json",
    "outFields": "*",
    "spatialRel": "esriSpatialRelIntersects",
    "where": "(outagestatus = 0) AND (datastatus = 'current')"
}

REQUEST_TIMEOUT = 30