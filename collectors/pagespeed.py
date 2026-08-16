"""
PageSpeed Insights Collector
"""
import requests


class PageSpeedCollector:

    def __init__(self, api_key: str, url: str):
        self.api_key = api_key
        self.target_url = url

    def collect(self) -> dict:
        if not self.target_url or "your-application" in (self.target_url or ""):
            return self._mock_data()

        try:
            params = {"url": self.target_url, "strategy": "desktop", "category": "performance"}
            if self.api_key:
                params["key"] = self.api_key

            print(f"  Querying PageSpeed for: {self.target_url}")
            resp = requests.get(
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                params=params, timeout=60
            )

            if resp.status_code != 200:
                print(f"  PageSpeed API error: {resp.status_code}")
                return self._mock_data()

            data = resp.json()
            audits = data.get("lighthouseResult", {}).get("audits", {})
            categories = data.get("lighthouseResult", {}).get("categories", {})

            def ms(key):
                return round(audits.get(key, {}).get("numericValue", 0), 0)

            return {
                "lcp": ms("largest-contentful-paint"),
                "cls": round(audits.get("cumulative-layout-shift", {}).get("numericValue", 0), 4),
                "tti": ms("interactive"),
                "fcp": ms("first-contentful-paint"),
                "speed_index": ms("speed-index"),
                "performance_score": round(categories.get("performance", {}).get("score", 0) * 100, 1)
            }

        except Exception as e:
            print(f"  PageSpeed failed: {e}")
            return self._mock_data()

    def _mock_data(self) -> dict:
        return {
            "lcp": 2400.0, "cls": 0.08, "tti": 3800.0,
            "fcp": 1200.0, "speed_index": 2100.0, "performance_score": 78.0
        }
