import math
import re
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait

from providers.base import BaseProvider
from scripts.utils import ARIZONA_TZ


class NISCOutageProvider(BaseProvider):
    """Shared reader for public NISC Outage Web Map installations."""

    MAP_URL = None

    def get_source(self):
        return f"{self.name.upper()} NISC Outage Web Map"

    def fetch_data(self):
        for attempt in range(3):
            try:
                records = self.scrape_records()
                break
            except WebDriverException as exc:
                if attempt == 2:
                    raise RuntimeError(
                        f"Failed to fetch {self.name.upper()} outage data: {exc}"
                    ) from exc
                time.sleep(2 ** attempt)

        return self.parse_records(records)

    def scrape_records(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,900")

        driver = webdriver.Chrome(options=options)
        try:
            driver.set_page_load_timeout(60)
            driver.get(self.MAP_URL)
            WebDriverWait(driver, 60).until(
                lambda browser: browser.execute_script(
                    "return !!document.getElementById('graphicsLayer3_layer');"
                )
            )

            # Wait for circle elements to be loaded and stable
            last_count = -1
            stable_count = 0
            for _ in range(10):
                try:
                    current_count = driver.execute_script(
                        "return document.querySelectorAll('#graphicsLayer3_layer circle').length;"
                    )
                    if current_count == last_count:
                        stable_count += 1
                        if stable_count >= 3:
                            break
                    else:
                        stable_count = 0
                        last_count = current_count
                except Exception:
                    pass
                time.sleep(1)

            return driver.execute_script("""
                const nodes = Array.from(
                    document.querySelectorAll('#graphicsLayer3_layer circle')
                );
                const records = [];
                const seen = new Set();

                // Find polygon layers for spatial checks
                let boundaryGraphics = [];
                try {
                    const firstCircle = document.querySelector('#graphicsLayer3_layer circle');
                    if (firstCircle && firstCircle.e_graphic) {
                        const layer = firstCircle.e_graphic._layer;
                        const map = layer.getMap ? layer.getMap() : layer._map;
                        if (map && map.graphicsLayerIds) {
                            for (let i = 0; i < map.graphicsLayerIds.length; i++) {
                                const gl = map.getLayer(map.graphicsLayerIds[i]);
                                if (gl && gl.graphics && gl.graphics.length > 0) {
                                    const sample = gl.graphics[0];
                                    if (sample && sample.geometry && sample.geometry.type === 'polygon') {
                                        boundaryGraphics = gl.graphics;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                } catch (e) {
                    // Ignore and fallback
                }

                function isPointInPolygon(point, polygon) {
                    if (!polygon || !polygon.rings) return false;
                    let inside = false;
                    const x = point.x;
                    const y = point.y;
                    for (let r = 0; r < polygon.rings.length; r++) {
                        const ring = polygon.rings[r];
                        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
                            const xi = ring[i][0], yi = ring[i][1];
                            const xj = ring[j][0], yj = ring[j][1];
                            const intersect = ((yi > y) !== (yj > y))
                                && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
                            if (intersect) inside = !inside;
                        }
                    }
                    return inside;
                }

                function getBoundaryName(point) {
                    if (!point) return null;
                    for (let i = 0; i < boundaryGraphics.length; i++) {
                        const g = boundaryGraphics[i];
                        if (g.geometry && g.geometry.type === 'polygon' && isPointInPolygon(point, g.geometry)) {
                            const attrs = g.attributes || {};
                            // Look for name-like attributes
                            for (const k in attrs) {
                                if (['name', 'label', 'boundary', 'district', 'region'].some(term => k.toLowerCase().includes(term))) {
                                    if (attrs[k]) return attrs[k];
                                }
                            }
                            // Fallback to first non-object attribute value
                            for (const k in attrs) {
                                if (typeof attrs[k] !== 'object' && attrs[k]) {
                                    return attrs[k];
                                }
                            }
                        }
                    }
                    return null;
                }

                for (const node of nodes) {
                    const graphic = node.e_graphic;
                    if (!graphic || seen.has(graphic)) continue;
                    seen.add(graphic);

                    graphic._graphicsLayer.onClick({
                        graphic: graphic,
                        mapPoint: graphic.geometry
                    });

                    const callout = document.querySelector('.mapviewer-callout');
                    const bName = getBoundaryName(graphic.geometry);
                    records.push({
                        x: graphic.geometry && graphic.geometry.x,
                        y: graphic.geometry && graphic.geometry.y,
                        text: callout ? callout.innerText : '',
                        boundary: bName
                    });
                }

                return records;
            """)
        finally:
            driver.quit()

    def parse_records(self, records):
        if not isinstance(records, list):
            raise ValueError(f"{self.name}: browser records must be a list")

        outages = []
        customers_affected = 0

        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"{self.name}: browser record must be an object")
            if not isinstance(record.get("text"), str) or not record["text"].strip():
                raise ValueError(f"{self.name}: outage card is missing text")
            if not isinstance(record.get("x"), (int, float)) or not isinstance(
                record.get("y"), (int, float)
            ):
                raise ValueError(f"{self.name}: outage card is missing coordinates")

            fields, status = self._parse_card(record.get("text") or "")
            customer_text = (
                fields.get("number out")
                or fields.get("customers affected")
                or fields.get("customers out")
            )
            if customer_text and re.search(r"\d", customer_text):
                customers = self._to_int(customer_text)
            else:
                customers = 0
            customers_affected += customers
            latitude, longitude = self._web_mercator_to_wgs84(
                record.get("x"), record.get("y")
            )

            outages.append({
                "latitude": latitude,
                "longitude": longitude,
                "customers": customers,
                "cause": fields.get("cause"),
                "comments": status,
                "start_time": self.format_time(
                    fields.get("outage reported at")
                    or fields.get("outage time")
                ),
                "etr": self.format_time(
                    fields.get("estimated time of restoration")
                    or fields.get("etr")
                ),
                "boundary": record.get("boundary")
            })

        return self.validate_snapshot({
            "metadata": self.build_metadata(),
            "summary": {
                "outage_count": len(outages),
                "customers_affected": customers_affected,
            },
            "outages": outages,
        })

    @staticmethod
    def _parse_card(text):
        lines = [
            line.strip().lstrip("×").strip()
            for line in text.splitlines()
            if line.strip() and line.strip() != "×"
        ]
        lines = [line for line in lines if line.lower() != "outage details"]
        status = lines[0] if lines and ":" not in lines[0] else None
        fields = {}

        for line in lines[1:] if status else lines:
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip().lower()] = value.strip() or None

        return fields, status

    @staticmethod
    def _to_int(value):
        if not value:
            return 0
        match = re.search(r"[\d,]+", value)
        return int(match.group().replace(",", "")) if match else 0

    @staticmethod
    def _web_mercator_to_wgs84(x, y):
        if x is None or y is None:
            return None, None
        longitude = x * 180 / 20037508.34
        latitude = math.degrees(
            2 * math.atan(math.exp(math.radians(y * 180 / 20037508.34)))
            - math.pi / 2
        )
        return latitude, longitude

    @staticmethod
    def format_time(value, reference=None):
        if not value:
            return None

        reference = reference or datetime.now(ARIZONA_TZ)
        for date_format in ("%m/%d %I:%M %p", "%m/%d/%Y %I:%M %p"):
            try:
                if "%Y" not in date_format:
                    temp_value = f"{value} {reference.year}"
                    temp_format = f"{date_format} %Y"
                    parsed = datetime.strptime(temp_value, temp_format)
                    delta = parsed.replace(tzinfo=ARIZONA_TZ) - reference
                    if delta.days > 183:
                        parsed = parsed.replace(year=reference.year - 1)
                    elif delta.days < -183:
                        parsed = parsed.replace(year=reference.year + 1)
                else:
                    parsed = datetime.strptime(value, date_format)
                return parsed.replace(tzinfo=ARIZONA_TZ).strftime(
                    "%Y-%m-%d %H:%M:%S %Z"
                )
            except ValueError:
                continue

        return None
