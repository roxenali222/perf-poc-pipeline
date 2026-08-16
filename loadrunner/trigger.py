"""
LoadRunner Test Trigger
-----------------------
Runs Journey 1 (Login & Browse) + Journey 2 (Search & Checkout)
Both journeys have Dynatrace tagging headers

Production: Replace with real LoadRunner CLI or LRE REST API
"""
import time
import os
from datetime import datetime

from loadrunner.journey1_login_browse import Journey1LoginBrowse
from loadrunner.journey2_search_checkout import Journey2SearchCheckout


class LoadRunnerTrigger:

    def __init__(self, base_url: str, duration_seconds: int = 60, vus: int = 5):
        self.base_url = base_url.rstrip("/")
        self.duration = duration_seconds
        self.vus = vus

        # Service URLs
        self.product_url = os.getenv("PRODUCT_SERVICE_URL", base_url)
        self.user_url = os.getenv("USER_SERVICE_URL", "http://20.81.60.76")
        self.order_url = os.getenv("ORDER_SERVICE_URL", "http://57.152.89.143")

    def run(self) -> dict:
        """
        Run both LoadRunner journeys.

        TODO — Production Integration:
        --------------------------------
        Option 1: LoadRunner Enterprise REST API
            return self._trigger_lr_enterprise()

        Option 2: Parse LoadRunner results file
            return self._parse_lr_results("results/output.csv")

        NOTE: Real LR scripts must include Dynatrace headers:
            X-Dynatrace-Test: true
            X-Test-Name: your-test-name
            X-Service-Name: service-name
            X-Cluster: cluster-name
        --------------------------------
        """
        print(f"\n  LoadRunner Test Starting...")
        print(f"  Product: {self.product_url}")
        print(f"  User:    {self.user_url}")
        print(f"  Order:   {self.order_url}")
        print(f"  Duration: {self.duration}s")

        start_time = datetime.now().isoformat()
        all_results = []
        total = 0
        failed = 0
        all_rt = []

        # Run iterations for duration
        start = time.time()
        iteration = 0

        while time.time() - start < self.duration:
            iteration += 1
            print(f"\n  --- Iteration {iteration} ---")

            # Journey 1 — Login & Browse
            j1 = Journey1LoginBrowse(
                product_url=self.product_url,
                user_url=self.user_url
            )
            j1_result = j1.run()
            all_results.append(j1_result)

            for step in j1_result["steps"]:
                total += 1
                all_rt.append(step["duration_ms"])
                if not step["success"]:
                    failed += 1

            # Journey 2 — Search & Checkout
            j2 = Journey2SearchCheckout(
                product_url=self.product_url,
                order_url=self.order_url,
                user_url=self.user_url
            )
            j2_result = j2.run()
            all_results.append(j2_result)

            for step in j2_result["steps"]:
                total += 1
                all_rt.append(step["duration_ms"])
                if not step["success"]:
                    failed += 1

            # Check if duration exceeded
            if time.time() - start >= self.duration:
                break

        # Calculate summary
        elapsed = time.time() - start
        all_rt.sort()

        avg_rt = round(sum(all_rt) / len(all_rt), 2) if all_rt else 0
        p90 = round(all_rt[int(len(all_rt) * 0.9)], 2) if all_rt else 0
        throughput = round((total / elapsed) * 60, 1) if elapsed > 0 else 0
        error_rate = round((failed / total) * 100, 2) if total > 0 else 0

        print(f"\n  {'='*40}")
        print(f"  LOAD TEST COMPLETE")
        print(f"  {'='*40}")
        print(f"  Iterations:       {iteration}")
        print(f"  Total Requests:   {total}")
        print(f"  Failed:           {failed}")
        print(f"  Avg Response:     {avg_rt}ms")
        print(f"  P90 Response:     {p90}ms")
        print(f"  Throughput:       {throughput} req/min")
        print(f"  Error Rate:       {error_rate}%")

        return {
            "total_requests": total,
            "failed_requests": failed,
            "avg_response_time_ms": avg_rt,
            "p90_response_time_ms": p90,
            "throughput_per_min": throughput,
            "error_rate_pct": error_rate,
            "start_time": start_time,
            "end_time": datetime.now().isoformat(),
            "iterations": iteration,
            "journeys": all_results
        }

    def _parse_lr_results(self, results_file: str) -> dict:
        """Parse LoadRunner CSV results file"""
        import csv
        response_times = []
        failed = 0
        total = 0

        try:
            with open(results_file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total += 1
                    rt = float(row.get("response_time", 0))
                    response_times.append(rt)
                    if int(row.get("status_code", 200)) >= 400:
                        failed += 1

            response_times.sort()
            return {
                "total_requests": total,
                "failed_requests": failed,
                "avg_response_time_ms": round(sum(response_times) / len(response_times), 2) if response_times else 0,
                "p90_response_time_ms": round(response_times[int(len(response_times) * 0.9)], 2) if response_times else 0,
                "throughput_per_min": 0,
                "error_rate_pct": round((failed / total) * 100, 2) if total > 0 else 0,
            }
        except Exception as e:
            print(f"  LR results parse error: {e}")
            return {}

    def _trigger_lr_enterprise(self) -> dict:
        """Trigger LoadRunner Enterprise via REST API"""
        import requests

        LRE_URL = os.getenv("LRE_URL", "")
        LRE_TOKEN = os.getenv("LRE_TOKEN", "")
        TEST_ID = os.getenv("LRE_TEST_ID", "1")

        headers = {"Authorization": f"Bearer {LRE_TOKEN}", "Content-Type": "application/json"}

        resp = requests.post(
            f"{LRE_URL}/api/v1/test-runs",
            headers=headers,
            json={"testId": TEST_ID},
            timeout=30
        )

        run_id = resp.json().get("runId")
        print(f"  LRE test started: {run_id}")

        while True:
            status = requests.get(f"{LRE_URL}/api/v1/test-runs/{run_id}", headers=headers).json().get("status")
            if status == "Finished":
                break
            print(f"  Status: {status}...")
            time.sleep(30)

        data = requests.get(f"{LRE_URL}/api/v1/test-runs/{run_id}/results", headers=headers).json()

        return {
            "total_requests": data.get("totalRequests", 0),
            "failed_requests": data.get("failedRequests", 0),
            "avg_response_time_ms": data.get("avgResponseTime", 0),
            "p90_response_time_ms": data.get("p90ResponseTime", 0),
            "throughput_per_min": data.get("throughput", 0),
            "error_rate_pct": data.get("errorRate", 0),
        }
