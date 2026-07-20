import os
import csv
import io
import logging
from datetime import datetime
from flask import Flask, jsonify, request, render_template, Response

from dashboard.archive_reader import scan_archive, archive_fingerprint
from dashboard.filters import apply_filters, strip_tz
from scripts.utils import ARIZONA_TZ

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("outage_dashboard")

app = Flask(__name__, template_folder="templates", static_folder="static")

# Environment configurations with safe defaults
HOST = os.environ.get("HOST", "0.0.0.0")
try:
    PORT = int(os.environ.get("PORT", 5000))
except ValueError:
    PORT = 5000
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
DATA_DIR = os.environ.get("DATA_DIR", "data")
try:
    AUTO_REFRESH_SECONDS = int(os.environ.get("AUTO_REFRESH_SECONDS", 60))
except ValueError:
    AUTO_REFRESH_SECONDS = 60

@app.route("/")
def index():
    return render_template("index.html", auto_refresh_seconds=AUTO_REFRESH_SECONDS)

@app.route("/api/health")
def health():
    return jsonify({"status": "healthy"})

@app.route("/api/file-status")
def file_status():
    """
    Returns a lightweight fingerprint of the archive directory.
    Useful for frontend polling to detect additions/modifications.
    """
    file_count, max_mtime = archive_fingerprint(DATA_DIR)
    return jsonify({
        "file_count": file_count,
        "max_mtime": max_mtime
    })

@app.route("/api/metadata")
def metadata():
    """
    Returns archive metadata including provider lists, date boundaries,
    snapshot counts, list of unique causes, and quality counts.
    """
    try:
        snapshots, stats = scan_archive(DATA_DIR)
    except Exception as e:
        logger.exception("Error in /api/metadata scan")
        return jsonify({"error": f"Failed to read archive: {e}"}), 500

    providers = sorted(list(set(s["provider"] for s in snapshots)))
    
    # Date boundaries
    times = [s["scraped_at"] for s in snapshots if s.get("scraped_at")]
    earliest = min(times) if times else None
    latest = max(times) if times else None

    # Latest snapshot by provider
    latest_by_provider = {}
    for s in snapshots:
        prov = s["provider"]
        if prov not in latest_by_provider or s["scraped_at"] > latest_by_provider[prov]:
            latest_by_provider[prov] = s["scraped_at"]

    # Gather unique causes
    causes = set()
    for s in snapshots:
        for out in s["outages"]:
            cause = out.get("cause")
            if cause:
                causes.add(str(cause).strip())

    return jsonify({
        "providers": providers,
        "date_bounds": {
            "earliest": earliest,
            "latest": latest
        },
        "snapshot_count": stats.total_snapshots,
        "latest_snapshot_by_provider": latest_by_provider,
        "available_causes": sorted(list(causes)),
        "data_quality_counts": {
            "malformed_files": stats.malformed_files,
            "missing_coords": stats.missing_coords,
            "invalid_coords": stats.invalid_coords
        }
    })

def parse_filter_params():
    """
    Extracts and parses filter query parameters from the request.
    """
    params = {}
    
    # Providers (supports multi-select comma separated or repeated params)
    provs = request.args.getlist("providers")
    if len(provs) == 1 and "," in provs[0]:
        provs = provs[0].split(",")
    params["providers"] = [p.strip().lower() for p in provs if p.strip()]

    params["start_date"] = request.args.get("start_date")
    params["end_date"] = request.args.get("end_date")
    params["time_of_day_start"] = request.args.get("time_of_day_start")
    params["time_of_day_end"] = request.args.get("time_of_day_end")
    params["min_customers"] = request.args.get("min_customers")
    params["max_customers"] = request.args.get("max_customers")
    params["cause"] = request.args.get("cause")
    params["active_only"] = request.args.get("active_only", "false").lower() == "true"
    params["include_unknown_customers"] = request.args.get("include_unknown_customers", "false").lower() == "true"
    params["display_mode"] = request.args.get("display_mode", "latest")
    params["snapshot_time"] = request.args.get("snapshot_time")

    return params

@app.route("/api/outages")
def outages():
    """
    Returns filtered and normalized outage records plus summary details.
    """
    params = parse_filter_params()
    try:
        snapshots, _ = scan_archive(DATA_DIR)
        filtered_outages, summary = apply_filters(snapshots, params)
    except Exception as e:
        logger.exception("Error in /api/outages processing")
        return jsonify({"error": f"Internal query execution failed: {e}"}), 500

    return jsonify({
        "summary": summary,
        "outages": filtered_outages
    })

@app.route("/api/timeline")
def timeline():
    """
    Returns aggregate time series datapoints for lines charts representing
    total outages and customers affected over time.
    """
    params = parse_filter_params()
    # Force mode to historical or override display limits so we can see timeline
    # We want to filter snapshots based on date/provider range, then aggregate
    try:
        snapshots, _ = scan_archive(DATA_DIR)
    except Exception as e:
        logger.exception("Error in /api/timeline data load")
        return jsonify({"error": str(e)}), 500

    # Filter snapshots down by provider and date range
    selected_providers = params.get("providers", [])
    start_date = params.get("start_date")
    end_date = params.get("end_date")

    # Narrow down snapshots list
    snaps = list(snapshots)
    if selected_providers:
        snaps = [s for s in snaps if s["provider"] in selected_providers]
        
    filtered_snaps = []
    for s in snaps:
        time_ok = True
        sa = strip_tz(s["scraped_at"])
        if start_date:
            sd = start_date if " " in start_date else f"{start_date} 00:00:00"
            if sa < strip_tz(sd):
                time_ok = False
        if end_date:
            ed = end_date if " " in end_date else f"{end_date} 23:59:59"
            if sa > strip_tz(ed):
                time_ok = False
        if time_ok:
            filtered_snaps.append(s)

    # Sort cronologically
    filtered_snaps.sort(key=lambda s: s["scraped_at"])

    # Aggregate records per snapshot
    # Respecting filters like cause, min_customers, active_only, etc.
    min_customers = params.get("min_customers")
    max_customers = params.get("max_customers")
    cause_query = params.get("cause")
    active_only = params.get("active_only", False)
    include_unknown_customers = params.get("include_unknown_customers", False)
    time_of_day_start = params.get("time_of_day_start")
    time_of_day_end = params.get("time_of_day_end")

    try:
        min_customers = int(min_customers) if min_customers is not None and min_customers != "" else None
    except ValueError:
        min_customers = None
    try:
        max_customers = int(max_customers) if max_customers is not None and max_customers != "" else None
    except ValueError:
        max_customers = None

    timeline_points = []
    for s in filtered_snaps:
        outages_count = 0
        customers_affected = 0
        for out in s["outages"]:
            # Apply outage levels
            if cause_query:
                cause = out.get("cause") or ""
                comments = out.get("comments") or ""
                q = str(cause_query).lower()
                if q not in cause.lower() and q not in comments.lower():
                    continue

            if active_only and out.get("restored_time") is not None:
                continue

            cust = out.get("customers", 0)
            is_unknown = (cust == 0)
            if is_unknown and include_unknown_customers:
                pass
            else:
                if min_customers is not None and cust < min_customers:
                    continue
                if max_customers is not None and cust > max_customers:
                    continue

            if time_of_day_start or time_of_day_end:
                st = out.get("start_time")
                if not st:
                    continue
                parts = st.split(" ")
                if len(parts) < 2:
                    continue
                t_part = parts[1][:5]
                if time_of_day_start and t_part < time_of_day_start:
                    continue
                if time_of_day_end and t_part > time_of_day_end:
                    continue

            outages_count += 1
            customers_affected += cust

        timeline_points.append({
            "timestamp": s["scraped_at"],
            "outages_count": outages_count,
            "customers_affected": customers_affected,
            "provider": s["provider"]
        })

    return jsonify(timeline_points)

@app.route("/api/export.csv")
def export_csv():
    """
    Streams a CSV file containing the active filtered normalized records.
    """
    params = parse_filter_params()
    try:
        snapshots, _ = scan_archive(DATA_DIR)
        filtered_outages, _ = apply_filters(snapshots, params)
    except Exception as e:
        logger.exception("Error in CSV export")
        return f"Error creating CSV export: {e}", 500

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Provider", "Customers Affected", "Cause", "Comments", 
            "Start Time", "Estimated Restoration (ETR)", "Restored Time", 
            "Latitude", "Longitude", "City", "Boundary", "Incident ID", 
            "Pole Number", "Event", "Division", "Snapshot Time"
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for out in filtered_outages:
            writer.writerow([
                out.get("provider", "").upper(),
                out.get("customers", 0),
                out.get("cause") or "",
                out.get("comments") or "",
                out.get("start_time") or "",
                out.get("etr") or "",
                out.get("restored_time") or "",
                out.get("latitude") if out.get("latitude") is not None else "",
                out.get("longitude") if out.get("longitude") is not None else "",
                out.get("city") or "",
                out.get("boundary") or "",
                out.get("incident_id") or "",
                out.get("pole_number") or "",
                out.get("event") or "",
                out.get("division") or "",
                out.get("snapshot_time") or ""
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    response = Response(generate(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=outages_export.csv"
    return response

if __name__ == "__main__":
    logger.info(f"Starting Arizona Power Outage Explorer on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=FLASK_DEBUG)
