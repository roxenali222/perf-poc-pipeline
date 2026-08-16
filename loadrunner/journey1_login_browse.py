"""
LoadRunner Journey 1 — Login & Browse
======================================
Real LoadRunner script simulation in Python.

For actual LoadRunner VuGen:
- Copy HTTP requests to VuGen script
- Add Dynatrace headers to each request
- Set think times same as here

Dynatrace Tagging Headers (ADD TO EVERY LR REQUEST):
  X-Dynatrace-Test: true
  X-Test-Name: journey1-login-browse
  X-Service-Name: product-service,user-service
  X-Cluster: perf-poc-aks
"""
import requests
import time
import random
from datetime import datetime

# Dynatrace tagging headers
DT_HEADERS = {
    "X-Dynatrace-Test": "true",
    "X-Test-Name": "journey1-login-browse",
    "X-Service-Name": "user-service,product-service",
    "X-Cluster": "perf-poc-aks",
    "X-Environment": "staging",
    "User-Agent": "LoadRunner/2023"
}


class Journey1LoginBrowse:
    """
    User Journey 1: Login → Browse Products → View Product Detail
    
    Steps:
    1. GET  /health          (warmup)
    2. POST /api/auth/login  (login)
    3. GET  /api/products    (browse)
    4. GET  /api/products/search?q=laptop (search)
    5. GET  /api/products/1  (view detail)
    6. GET  /api/products/2  (view another)
    7. POST /api/auth/logout (logout)
    """

    def __init__(self, product_url: str, user_url: str):
        self.product_url = product_url.rstrip("/")
        self.user_url = user_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(DT_HEADERS)
        self.results = []
        self.token = None

    def _think_time(self, min_sec=1.0, max_sec=3.0):
        """Simulate user think time"""
        time.sleep(random.uniform(min_sec, max_sec))

    def _record(self, step: str, response, start_time: float):
        duration = (time.time() - start_time) * 1000
        success = response is not None and response.status_code < 400
        self.results.append({
            "step": step,
            "status_code": response.status_code if response else 0,
            "duration_ms": round(duration, 2),
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        icon = "✅" if success else "❌"
        print(f"    {icon} {step}: {round(duration, 2)}ms (HTTP {response.status_code if response else 'ERR'})")

    def step_01_health_check(self):
        start = time.time()
        try:
            resp = self.session.get(f"{self.product_url}/health", timeout=10)
            self._record("01_HealthCheck", resp, start)
        except Exception as e:
            print(f"    ❌ 01_HealthCheck failed: {e}")
        self._think_time(0.5, 1.0)

    def step_02_login(self):
        start = time.time()
        try:
            resp = self.session.post(
                f"{self.user_url}/api/auth/login",
                json={"username": "john@example.com", "password": "test123"},
                timeout=10
            )
            self._record("02_Login", resp, start)
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("token", "")
                if self.token:
                    self.session.headers["Authorization"] = f"Bearer {self.token}"
        except Exception as e:
            print(f"    ❌ 02_Login failed: {e}")
        self._think_time(2, 4)

    def step_03_browse_products(self):
        start = time.time()
        try:
            resp = self.session.get(
                f"{self.product_url}/api/products",
                params={"page": 1, "limit": 10},
                timeout=10
            )
            self._record("03_BrowseProducts", resp, start)
        except Exception as e:
            print(f"    ❌ 03_BrowseProducts failed: {e}")
        self._think_time(2, 5)

    def step_04_search(self):
        start = time.time()
        try:
            resp = self.session.get(
                f"{self.product_url}/api/products/search",
                params={"q": "laptop"},
                timeout=10
            )
            self._record("04_SearchProducts", resp, start)
        except Exception as e:
            print(f"    ❌ 04_SearchProducts failed: {e}")
        self._think_time(2, 4)

    def step_05_view_product(self, product_id=1):
        start = time.time()
        try:
            resp = self.session.get(
                f"{self.product_url}/api/products/{product_id}",
                timeout=10
            )
            self._record(f"05_ViewProduct_{product_id}", resp, start)
        except Exception as e:
            print(f"    ❌ 05_ViewProduct failed: {e}")
        self._think_time(3, 6)

    def step_06_view_another_product(self, product_id=3):
        start = time.time()
        try:
            resp = self.session.get(
                f"{self.product_url}/api/products/{product_id}",
                timeout=10
            )
            self._record(f"06_ViewProduct_{product_id}", resp, start)
        except Exception as e:
            print(f"    ❌ 06_ViewProduct failed: {e}")
        self._think_time(2, 4)

    def step_07_logout(self):
        start = time.time()
        try:
            resp = self.session.post(
                f"{self.user_url}/api/auth/logout",
                timeout=10
            )
            self._record("07_Logout", resp, start)
        except Exception as e:
            print(f"    ❌ 07_Logout failed: {e}")

    def run(self) -> dict:
        print(f"\n  🚀 Journey 1: Login & Browse")
        print(f"     Product URL: {self.product_url}")
        print(f"     User URL:    {self.user_url}")

        self.step_01_health_check()
        self.step_02_login()
        self.step_03_browse_products()
        self.step_04_search()
        self.step_05_view_product(1)
        self.step_06_view_another_product(3)
        self.step_07_logout()

        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        avg_rt = sum(r["duration_ms"] for r in self.results) / total if total else 0
        p90_idx = int(total * 0.9)
        sorted_rt = sorted(r["duration_ms"] for r in self.results)
        p90 = sorted_rt[p90_idx] if sorted_rt else 0

        summary = {
            "journey": "Login & Browse",
            "total_steps": total,
            "passed": passed,
            "failed": total - passed,
            "avg_duration_ms": round(avg_rt, 2),
            "p90_duration_ms": round(p90, 2),
            "steps": self.results
        }

        print(f"\n     Results: {passed}/{total} passed | Avg: {round(avg_rt, 2)}ms | P90: {round(p90, 2)}ms")
        return summary
