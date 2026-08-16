"""
LoadRunner Journey 2 — Search & Checkout
==========================================
Real LoadRunner script simulation in Python.

For actual LoadRunner VuGen:
- Copy HTTP requests to VuGen script
- Add Dynatrace headers to each request

Dynatrace Tagging Headers (ADD TO EVERY LR REQUEST):
  X-Dynatrace-Test: true
  X-Test-Name: journey2-search-checkout
  X-Service-Name: product-service,order-service
  X-Cluster: perf-poc-aks
"""
import requests
import time
import random
from datetime import datetime

DT_HEADERS = {
    "X-Dynatrace-Test": "true",
    "X-Test-Name": "journey2-search-checkout",
    "X-Service-Name": "product-service,order-service",
    "X-Cluster": "perf-poc-aks",
    "X-Environment": "staging",
    "User-Agent": "LoadRunner/2023"
}


class Journey2SearchCheckout:
    """
    User Journey 2: Search → Add to Cart → Checkout → Confirm

    Steps:
    1. GET  /api/products/search?q=laptop  (search)
    2. GET  /api/products/2               (view product)
    3. POST /api/cart/add                 (add to cart)
    4. GET  /api/cart                     (view cart) 
    5. POST /api/checkout/shipping        (enter shipping)
    6. POST /api/checkout/payment         (enter payment)
    7. POST /api/checkout/confirm         (confirm order)
    8. GET  /api/orders                   (view orders)
    """

    def __init__(self, product_url: str, order_url: str, user_url: str):
        self.product_url = product_url.rstrip("/")
        self.order_url = order_url.rstrip("/")
        self.user_url = user_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(DT_HEADERS)
        self.results = []
        self.cart_id = None

    def _think_time(self, min_sec=2.0, max_sec=5.0):
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

    def step_01_search(self, query="laptop"):
        start = time.time()
        try:
            resp = self.session.get(
                f"{self.product_url}/api/products/search",
                params={"q": query},
                timeout=10
            )
            self._record("01_Search", resp, start)
        except Exception as e:
            print(f"    ❌ 01_Search failed: {e}")
        self._think_time(2, 4)

    def step_02_view_product(self, product_id=2):
        start = time.time()
        try:
            resp = self.session.get(
                f"{self.product_url}/api/products/{product_id}",
                timeout=10
            )
            self._record("02_ViewProduct", resp, start)
        except Exception as e:
            print(f"    ❌ 02_ViewProduct failed: {e}")
        self._think_time(3, 6)

    def step_03_add_to_cart(self, product_id=2):
        start = time.time()
        try:
            resp = self.session.post(
                f"{self.order_url}/api/cart/add",
                json={"product_id": product_id, "quantity": 1},
                timeout=10
            )
            self._record("03_AddToCart", resp, start)
            if resp.status_code == 200:
                self.cart_id = resp.json().get("cart_id", f"cart_{int(time.time())}")
        except Exception as e:
            print(f"    ❌ 03_AddToCart failed: {e}")
        self._think_time(1, 2)

    def step_04_view_cart(self):
        start = time.time()
        try:
            resp = self.session.get(
                f"{self.order_url}/api/cart",
                timeout=10
            )
            self._record("04_ViewCart", resp, start)
        except Exception as e:
            print(f"    ❌ 04_ViewCart failed: {e}")
        self._think_time(2, 4)

    def step_05_shipping(self):
        start = time.time()
        try:
            resp = self.session.post(
                f"{self.order_url}/api/checkout/shipping",
                json={
                    "name": "Test User",
                    "address": "123 Test Street",
                    "city": "New York",
                    "zip": "10001",
                    "country": "US"
                },
                timeout=10
            )
            self._record("05_Shipping", resp, start)
        except Exception as e:
            print(f"    ❌ 05_Shipping failed: {e}")
        self._think_time(4, 8)

    def step_06_payment(self):
        start = time.time()
        try:
            resp = self.session.post(
                f"{self.order_url}/api/checkout/payment",
                json={
                    "card_type": "visa",
                    "card_last4": "4242",
                    "expiry": "12/26"
                },
                timeout=10
            )
            self._record("06_Payment", resp, start)
        except Exception as e:
            print(f"    ❌ 06_Payment failed: {e}")
        self._think_time(2, 3)

    def step_07_confirm_order(self):
        start = time.time()
        try:
            resp = self.session.post(
                f"{self.order_url}/api/checkout/confirm",
                json={"cart_id": self.cart_id},
                timeout=30
            )
            self._record("07_ConfirmOrder", resp, start)
        except Exception as e:
            print(f"    ❌ 07_ConfirmOrder failed: {e}")
        self._think_time(1, 2)

    def step_08_view_orders(self):
        start = time.time()
        try:
            resp = self.session.get(
                f"{self.order_url}/api/orders",
                timeout=10
            )
            self._record("08_ViewOrders", resp, start)
        except Exception as e:
            print(f"    ❌ 08_ViewOrders failed: {e}")

    def run(self) -> dict:
        print(f"\n  🛒 Journey 2: Search & Checkout")
        print(f"     Product URL: {self.product_url}")
        print(f"     Order URL:   {self.order_url}")

        self.step_01_search("laptop")
        self.step_02_view_product(2)
        self.step_03_add_to_cart(2)
        self.step_04_view_cart()
        self.step_05_shipping()
        self.step_06_payment()
        self.step_07_confirm_order()
        self.step_08_view_orders()

        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        avg_rt = sum(r["duration_ms"] for r in self.results) / total if total else 0
        sorted_rt = sorted(r["duration_ms"] for r in self.results)
        p90 = sorted_rt[int(total * 0.9)] if sorted_rt else 0

        summary = {
            "journey": "Search & Checkout",
            "total_steps": total,
            "passed": passed,
            "failed": total - passed,
            "avg_duration_ms": round(avg_rt, 2),
            "p90_duration_ms": round(p90, 2),
            "steps": self.results
        }

        print(f"\n     Results: {passed}/{total} passed | Avg: {round(avg_rt, 2)}ms | P90: {round(p90, 2)}ms")
        return summary
