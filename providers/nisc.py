import math
import re
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
        try:
            records = self.scrape_records()
        except WebDriverException as exc:
            raise RuntimeError(
                f"Failed to fetch {self.name.upper()} outage data: {exc}"
            ) from exc

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

            return driver.execute_script("""
                const nodes = Array.from(
                    document.querySelectorAll('#graphicsLayer3_layer circle')
                );
                const records = [];
                const seen = new Set();

                for (const node of nodes) {
                    const graphic = node.e_graphic;
                    if (!graphic || seen.has(graphic)) continue;
                    seen.add(graphic);

                    graphic._graphicsLayer.onClick({
                        graphic: graphic,
                        mapPoint: graphic.geometry
                    });

                    const callout = document.querySelector('.mapviewer-callout');
                    records.push({
                        x: graphic.geometry && graphic.geometry.x,
                        y: graphic.geometry && graphic.geometry.y,
                        text: callout ? callout.innerText : ''
                    });
                }

                return records;
            """)
        finally:
            driver.quit()

    def parse_records(self, records):
        outages = []
        customers_affected = 0

        for record in records:
            fields, status = self._parse_card(record.get("text") or "")
            customers = self._to_int(
                fields.get("number out")
                or fields.get("customers affected")
                or fields.get("customers out")
            )
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
            })

        return {
            "metadata": self.build_metadata(),
            "summary": {
                "outage_count": len(outages),
                "customers_affected": customers_affected,
            },
            "outages": outages,
        }

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
                parsed = datetime.strptime(value, date_format)
                if "%Y" not in date_format:
                    parsed = parsed.replace(year=reference.year)
                    delta = parsed.replace(tzinfo=ARIZONA_TZ) - reference
                    if delta.days > 183:
                        parsed = parsed.replace(year=reference.year - 1)
                    elif delta.days < -183:
                        parsed = parsed.replace(year=reference.year + 1)
                return parsed.replace(tzinfo=ARIZONA_TZ).strftime(
                    "%Y-%m-%d %H:%M:%S %Z"
                )
            except ValueError:
                continue

        return None
