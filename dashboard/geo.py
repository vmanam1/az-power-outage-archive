import json
import math
import os

# Nearest-place lookup used to derive a City/Region for providers that do not
# publish one. Backed by the US Census 2023 gazetteer of Arizona incorporated
# places and CDPs (dashboard/az_places.json). Derived names are display-only:
# the archive files keep exactly what each utility published.

_PLACES_FILE = os.path.join(os.path.dirname(__file__), "az_places.json")

# Beyond this distance the nearest town stops being a meaningful label for an
# outage location (remote desert/forest land), so no name is derived.
MAX_DISTANCE_KM = 50.0

# Marks a derived (coordinate-based) value so it is never mistaken for a
# utility-published city.
DERIVED_PREFIX = "≈ "  # "≈ "

_places = None


def _load_places():
    global _places
    if _places is None:
        try:
            with open(_PLACES_FILE, encoding="utf-8") as f:
                _places = [
                    (name, math.radians(lat), math.radians(lng), lat)
                    for name, lat, lng in json.load(f)
                ]
        except (OSError, ValueError):
            _places = []
    return _places


def nearest_place(latitude, longitude):
    """
    Returns the name of the closest known Arizona place to the given WGS84
    coordinate, or None when the point is farther than MAX_DISTANCE_KM from
    everything (or the place list is unavailable).
    """
    places = _load_places()
    if not places or latitude is None or longitude is None:
        return None

    lat_r = math.radians(latitude)
    lng_r = math.radians(longitude)
    cos_lat = math.cos(lat_r)

    best_name = None
    best_sq = None
    for name, p_lat_r, p_lng_r, _ in places:
        # Equirectangular approximation: exact enough at state scale for a
        # nearest-neighbour argmin, and much cheaper than haversine.
        d_lat = p_lat_r - lat_r
        d_lng = (p_lng_r - lng_r) * cos_lat
        sq = d_lat * d_lat + d_lng * d_lng
        if best_sq is None or sq < best_sq:
            best_sq = sq
            best_name = name

    if best_sq is None:
        return None
    distance_km = math.sqrt(best_sq) * 6371.0
    if distance_km > MAX_DISTANCE_KM:
        return None
    return best_name


def derived_city(latitude, longitude):
    """
    Returns a display-ready derived city label ("≈ Marana") for a coordinate,
    or None when no meaningful place is nearby.
    """
    name = nearest_place(latitude, longitude)
    return f"{DERIVED_PREFIX}{name}" if name else None


# --- Co-op region polygons (display-only boundary backfill) -----------------
# dashboard/coop_regions.json holds each NISC co-op's named region polygons in
# absolute Web Mercator meters (see scripts/build_coop_regions.py). Snapshots
# archived before the collector learned region lookup lack a boundary; the
# dashboard fills it at read time from these polygons, marked with "≈".

_REGIONS_FILE = os.path.join(os.path.dirname(__file__), "coop_regions.json")
_regions = None


def _load_regions():
    global _regions
    if _regions is None:
        _regions = {}
        try:
            with open(_REGIONS_FILE, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            return _regions
        for provider, regions in raw.items():
            prepared = []
            for region in regions:
                rings = region.get("rings") or []
                if not rings:
                    continue
                xs = [pt[0] for ring in rings for pt in ring]
                ys = [pt[1] for ring in rings for pt in ring]
                prepared.append({
                    "name": region.get("name"),
                    "rings": rings,
                    # Bounding box lets most point tests skip the full
                    # point-in-polygon walk.
                    "bbox": (min(xs), min(ys), max(xs), max(ys)),
                })
            _regions[provider] = prepared
    return _regions


def _to_web_mercator(latitude, longitude):
    x = longitude / 180.0 * 20037508.34
    y = 6378137.0 * math.log(math.tan(math.pi / 4 + math.radians(latitude) / 2))
    return x, y


def _point_in_rings(px, py, rings):
    inside = False
    for ring in rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if (yi > py) != (yj > py) and px < (
                (xj - xi) * (py - yi) / (yj - yi) + xi
            ):
                inside = not inside
            j = i
    return inside


def derived_boundary(provider, latitude, longitude):
    """
    Returns a display-ready derived boundary ("≈ 5 - SPRINGERVILLE") by
    point-in-polygon testing the provider's region polygons, or None when the
    provider has none or the point matches nothing.
    """
    if latitude is None or longitude is None:
        return None
    regions = _load_regions().get(provider)
    if not regions:
        return None
    px, py = _to_web_mercator(latitude, longitude)
    for region in regions:
        x0, y0, x1, y1 = region["bbox"]
        if not (x0 <= px <= x1 and y0 <= py <= y1):
            continue
        if _point_in_rings(px, py, region["rings"]):
            name = region.get("name")
            return f"{DERIVED_PREFIX}{name}" if name else None
    return None
