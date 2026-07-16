import math
from datetime import datetime

def normalize_time(val):
    """
    Standardizes timezone-aware or naive MST/MDT date strings
    to a standard '%Y-%m-%d %H:%M:%S MST' format.
    """
    if not val:
        return None
    val_str = str(val).strip()
    
    # Clean up common MST suffixes
    clean_val = val_str
    for suffix in (" MST", " MDT", " UTC", " GMT"):
        if clean_val.endswith(suffix):
            clean_val = clean_val[:-len(suffix)]
            break

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(clean_val, fmt)
            return parsed.strftime("%Y-%m-%d %H:%M:%S MST")
        except ValueError:
            continue
    return None

def normalize_outage(outage, provider_name):
    """
    Normalizes an outage dictionary, validating coordinates and customer counts
    and formatting fields consistently.
    """
    # Customers
    customers = outage.get("customers")
    try:
        if isinstance(customers, bool):
            customers = 0
        elif isinstance(customers, int):
            if customers < 0:
                customers = 0
        elif isinstance(customers, str):
            customers = int(customers.replace(",", ""))
            if customers < 0:
                customers = 0
        else:
            customers = 0
    except (ValueError, TypeError):
        customers = 0

    # Coordinates
    lat = outage.get("latitude")
    lng = outage.get("longitude")
    
    has_coords = True
    if lat is None or lng is None:
        has_coords = False
    else:
        try:
            if isinstance(lat, bool) or isinstance(lng, bool):
                has_coords = False
            else:
                lat = float(lat)
                lng = float(lng)
                if not math.isfinite(lat) or not math.isfinite(lng):
                    has_coords = False
                elif not -90 <= lat <= 90 or not -180 <= lng <= 180:
                    has_coords = False
        except (ValueError, TypeError):
            has_coords = False

    if not has_coords:
        lat = None
        lng = None

    # Time fields
    start_time = normalize_time(outage.get("start_time"))
    etr = normalize_time(outage.get("etr"))
    restored_time = normalize_time(outage.get("restored_time"))
    last_update = normalize_time(outage.get("last_update"))

    # Optional division / restored count
    cust_restored = outage.get("customers_restored")
    if cust_restored is not None:
        try:
            if isinstance(cust_restored, bool):
                cust_restored = 0
            else:
                cust_restored = int(cust_restored)
        except (ValueError, TypeError):
            cust_restored = 0

    # Format dictionary boundaries to readable strings
    boundary = outage.get("boundary")
    if isinstance(boundary, dict):
        sw_lat = boundary.get("coordLatSW")
        sw_lng = boundary.get("coordLngSW")
        ne_lat = boundary.get("coordLatNE")
        ne_lng = boundary.get("coordLngNE")
        if sw_lat and sw_lng and ne_lat and ne_lng:
            try:
                boundary = f"Box: SW({float(sw_lat):.4f}, {float(sw_lng):.4f}) to NE({float(ne_lat):.4f}, {float(ne_lng):.4f})"
            except (ValueError, TypeError):
                boundary = str(boundary)
        else:
            boundary = str(boundary)
    elif boundary is not None:
        boundary = str(boundary).strip() or None

    return {
        "provider": provider_name.lower(),
        "latitude": lat,
        "longitude": lng,
        "customers": customers,
        "cause": outage.get("cause") or None,
        "comments": outage.get("comments") or None,
        "start_time": start_time,
        "etr": etr,
        "restored_time": restored_time,
        "city": outage.get("city") or None,
        "boundary": boundary,
        "incident_id": outage.get("incident_id") or None,
        "pole_number": outage.get("pole_number") or None,
        "event": outage.get("event") or None,
        "division": outage.get("division") or None,
        "customers_restored": cust_restored,
        "last_update": last_update,
        "has_coordinates": has_coords
    }
