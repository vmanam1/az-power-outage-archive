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
