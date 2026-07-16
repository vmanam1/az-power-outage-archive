from datetime import datetime
import re

def get_outage_key(outage):
    """
    Generates a unique key for deduplicating historical outages.
    Uses incident_id, pole_number, event, or falls back to rounded coordinates & start_time.
    """
    provider = outage.get("provider", "unknown")
    for field in ("incident_id", "pole_number", "event"):
        val = outage.get(field)
        if val:
            return f"{provider}_{field}_{val}"

    lat = outage.get("latitude")
    lng = outage.get("longitude")
    start_time = outage.get("start_time") or "unknown_start"

    if lat is not None and lng is not None:
        return f"{provider}_coords_{round(lat, 4)}_{round(lng, 4)}_start_{start_time}"

    boundary = outage.get("boundary") or outage.get("city") or "unknown_loc"
    return f"{provider}_boundary_{boundary}_start_{start_time}"

def apply_filters(snapshots, params):
    """
    Filters snapshots and outages based on the query parameters.
    Returns (filtered_outages, summary_dict).
    """
    # 1. Parse params
    selected_providers = params.get("providers", [])
    if isinstance(selected_providers, str):
        selected_providers = [selected_providers]
    selected_providers = [p.lower() for p in selected_providers if p]

    start_date = params.get("start_date")
    end_date = params.get("end_date")
    time_of_day_start = params.get("time_of_day_start") # HH:MM
    time_of_day_end = params.get("time_of_day_end") # HH:MM

    min_customers = params.get("min_customers")
    max_customers = params.get("max_customers")
    cause_query = params.get("cause")
    active_only = params.get("active_only", False)
    include_unknown_customers = params.get("include_unknown_customers", False)

    display_mode = params.get("display_mode", "latest")
    snapshot_time = params.get("snapshot_time")

    # Clean integers
    try:
        min_customers = int(min_customers) if min_customers is not None and min_customers != "" else None
    except ValueError:
        min_customers = None
    try:
        max_customers = int(max_customers) if max_customers is not None and max_customers != "" else None
    except ValueError:
        max_customers = None

    # Filter snapshots by provider first
    if selected_providers:
        prov_snapshots = [s for s in snapshots if s["provider"] in selected_providers]
    else:
        prov_snapshots = list(snapshots)

    # 2. Select snapshots based on display mode
    selected_snapshots = []
    
    if display_mode == "latest":
        # Newest snapshot per provider
        latest_snaps = {}
        for s in prov_snapshots:
            prov = s["provider"]
            if prov not in latest_snaps or s["scraped_at"] > latest_snaps[prov]["scraped_at"]:
                latest_snaps[prov] = s
        selected_snapshots = list(latest_snaps.values())

    elif display_mode == "snapshot_at_time":
        # Newest snapshot at or before snapshot_time per provider
        latest_snaps = {}
        target_time = snapshot_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S MST")
        for s in prov_snapshots:
            prov = s["provider"]
            if s["scraped_at"] <= target_time:
                if prov not in latest_snaps or s["scraped_at"] > latest_snaps[prov]["scraped_at"]:
                    latest_snaps[prov] = s
        selected_snapshots = list(latest_snaps.values())

    else:
        # historical or unique_outages -> filter snapshots in date range
        # Note: dates in scraped_at have format 'YYYY-MM-DD HH:MM:SS MST'.
        # If start_date/end_date are 'YYYY-MM-DD', they compare correctly.
        for s in prov_snapshots:
            time_ok = True
            if start_date:
                # Append min time if only date is given
                sd = start_date if " " in start_date else f"{start_date} 00:00:00"
                if s["scraped_at"] < sd:
                    time_ok = False
            if end_date:
                ed = end_date if " " in end_date else f"{end_date} 23:59:59"
                if s["scraped_at"] > ed:
                    time_ok = False
            if time_ok:
                selected_snapshots.append(s)

    # 3. Extract outages
    # Sort snapshots ascending by scraped_at to ensure proper ordering for deduplication
    selected_snapshots.sort(key=lambda s: s["scraped_at"])
    
    outages_list = []
    snapshot_files = set()
    
    for snap in selected_snapshots:
        snapshot_files.add(snap["file_path"])
        for out in snap["outages"]:
            # Copy and enrich with snapshot info
            out_copy = dict(out)
            out_copy["snapshot_time"] = snap["scraped_at"]
            out_copy["snapshot_file"] = snap["file_path"]
            outages_list.append(out_copy)

    # 4. Deduplicate if Unique Outages mode
    if display_mode == "unique_outages":
        unique_outages = {}
        for out in outages_list:
            key = get_outage_key(out)
            # Since snapshots were sorted ascending, the latest snapshot's record will overwrite older ones
            unique_outages[key] = out
        outages_list = list(unique_outages.values())

    # 5. Apply outage-level filters
    filtered_outages = []
    missing_coords_count = 0

    for out in outages_list:
        # Cause search
        if cause_query:
            cause = out.get("cause") or ""
            comments = out.get("comments") or ""
            q = str(cause_query).lower()
            if q not in cause.lower() and q not in comments.lower():
                continue

        # Active only
        if active_only:
            if out.get("restored_time") is not None:
                continue

        # Customers filter
        cust = out.get("customers", 0)
        # If it's 0 or unknown, we check if we should include unknown
        is_unknown = (cust == 0) # since we normalize missing/errors to 0
        if is_unknown and include_unknown_customers:
            # Bypass min/max customers limit
            pass
        else:
            if min_customers is not None and cust < min_customers:
                continue
            if max_customers is not None and cust > max_customers:
                continue

        # Time of day filter
        if time_of_day_start or time_of_day_end:
            st = out.get("start_time")
            if not st:
                continue
            # Extract time portion e.g., '14:50'
            parts = st.split(" ")
            if len(parts) < 2:
                continue
            t_part = parts[1][:5] # 'HH:MM'
            if time_of_day_start and t_part < time_of_day_start:
                continue
            if time_of_day_end and t_part > time_of_day_end:
                continue

        # Track missing coordinates count
        if not out.get("has_coordinates"):
            missing_coords_count += 1

        filtered_outages.append(out)

    # Calculate summary metrics
    visible_records = len(filtered_outages)
    total_customers = sum(o.get("customers", 0) for o in filtered_outages)
    
    unique_visible_providers = list(set(o["provider"] for o in filtered_outages))
    
    visible_snapshot_times = [o["snapshot_time"] for o in filtered_outages if o.get("snapshot_time")]
    earliest_visible_snapshot = min(visible_snapshot_times) if visible_snapshot_times else None
    latest_visible_snapshot = max(visible_snapshot_times) if visible_snapshot_times else None

    summary = {
        "visible_records": visible_records,
        "total_customers": total_customers,
        "provider_count": len(unique_visible_providers),
        "selected_providers": unique_visible_providers,
        "snapshot_files_count": len(snapshot_files),
        "earliest_visible_snapshot": earliest_visible_snapshot,
        "latest_visible_snapshot": latest_visible_snapshot,
        "missing_coords_count": missing_coords_count
    }

    return filtered_outages, summary
