"""
Dynatrace Metrics Collector

CPU / Memory strategy (in priority order):
  1. v2 Metrics Query API   -> /api/v2/metrics/query   (needs scope: metrics.read)
  2. v1 Timeseries API      -> /api/v1/timeseries/...   (needs scope: DataExport, legacy)
  3. Mock fallback          -> so the pipeline never hard-fails in a demo

The v2 API is the correct/modern path. It needs a CLASSIC Access Token
(prefix dt0c01...) with the "Read metrics" (metrics.read) scope ticked.
metrics.read is a CLASSIC token scope -- it does NOT exist on OAuth clients or
Platform tokens (those use storage:metrics:read for Grail/DQL instead).

Metric keys can be overridden from .env so you can point them at whatever your
tenant actually exposes (host-level vs pod/workload-level):

  DT_CPU_METRIC   default builtin:host.cpu.usage
  DT_MEM_METRIC   default builtin:host.mem.usage
  DT_METRIC_ENTITY_SELECTOR  optional, e.g. type(HOST) or type(CLOUD_APPLICATION),entityName("product-service")
"""
import os
import requests
from datetime import datetime, timedelta, timezone


class DynatraceCollector:

    def __init__(self, url: str, token: str, entity_selector: str = None):
        self.url = url.rstrip("/")
        self.token = token
        self.headers = {
            "Authorization": f"Api-Token {token}",
            "Content-Type": "application/json",
        }
        self._lr_results = {}

        # CPU / Memory metric keys — override per environment via .env
        self.cpu_metric = os.getenv("DT_CPU_METRIC", "builtin:host.cpu.usage")
        self.mem_metric = os.getenv("DT_MEM_METRIC", "builtin:host.mem.usage")
        self.metric_entity_selector = os.getenv("DT_METRIC_ENTITY_SELECTOR", "").strip() or None

    def set_lr_results(self, lr_results: dict):
        self._lr_results = lr_results

    # ── helpers ────────────────────────────────────────────────────────────
    def _time_range_ms(self, minutes: int = 30):
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=minutes)
        return int(start.timestamp() * 1000), int(now.timestamp() * 1000)

    def _query_v2_metric(self, metric_selector: str, entity_selector: str = None,
                         aggregation: str = "avg", minutes: int = 30):
        """
        Modern path. GET /api/v2/metrics/query  (scope: metrics.read)
        resolution=Inf collapses each series to a single aggregated value.
        Returns a float, or raises PermissionError on 403 (scope missing).
        """
        params = {
            "metricSelector": f"{metric_selector}:{aggregation}",
            "from": f"now-{minutes}m",
            "to": "now",
            "resolution": "Inf",
        }
        sel = entity_selector or self.metric_entity_selector
        if sel:
            params["entitySelector"] = sel

        resp = requests.get(
            f"{self.url}/api/v2/metrics/query",
            headers=self.headers, params=params, timeout=30,
        )
        if resp.status_code == 403:
            raise PermissionError(
                "403 from /api/v2/metrics/query -> token is missing the "
                "metrics.read scope (use a CLASSIC dt0c01 token)."
            )
        if resp.status_code == 400:
            # usually a bad metric key for this tenant
            raise ValueError(f"400 for metricSelector '{metric_selector}': {resp.text[:200]}")
        resp.raise_for_status()

        result = resp.json().get("result", [])
        values = []
        for group in result:
            for series in group.get("data", []):
                for v in series.get("values", []):
                    if v is not None:
                        values.append(v)
        if values:
            return round(sum(values) / len(values), 2)
        return None

    def _query_v1_timeseries(self, timeseries_id: str, aggregation: str = "AVG"):
        """Legacy path. POST /api/v1/timeseries  (scope: DataExport)."""
        try:
            from_ms, to_ms = self._time_range_ms(30)
            resp = requests.post(
                f"{self.url}/api/v1/timeseries/{timeseries_id}",
                headers=self.headers,
                json={
                    "aggregationType": aggregation,
                    "startTimestamp": from_ms,
                    "endTimestamp": to_ms,
                    "queryMode": "TOTAL",
                },
                timeout=30,
            )
            if resp.status_code == 200:
                datapoints = resp.json().get("dataPoints", {})
                all_values = []
                for entity_points in datapoints.values():
                    for point in entity_points:
                        if point and len(point) > 1 and point[1] is not None:
                            all_values.append(point[1])
                if all_values:
                    return round(sum(all_values) / len(all_values), 2)
            return None
        except Exception:
            return None

    def _cpu_mem(self, kind: str, v2_metric: str, v1_id: str, mock: float):
        """Try v2, then v1, then mock. Returns (value, source_label)."""
        try:
            val = self._query_v2_metric(v2_metric)
            if val is not None:
                return val, "Dynatrace v2"
        except PermissionError as e:
            print(f"  {kind}: {e}")
        except Exception as e:
            print(f"  {kind}: v2 query failed ({e}); trying v1")

        val = self._query_v1_timeseries(v1_id)
        if val is not None:
            return val, "Dynatrace v1"

        return mock, "mock"

    # ── main collection ────────────────────────────────────────────────────
    def collect(self) -> dict:
        print(f"  Querying Dynatrace: {self.url}")
        metrics = {}

        # ── LoadRunner metrics (always available) ──
        if self._lr_results:
            metrics["response_time_avg"] = self._lr_results.get("avg_response_time_ms", 0)
            metrics["p90_response_time_ms"] = self._lr_results.get("p90_response_time_ms", 0)
            metrics["error_rate"] = self._lr_results.get("error_rate_pct", 0)
            metrics["throughput"] = self._lr_results.get("throughput_per_min", 0)
            print(f"  response_time_avg: {metrics['response_time_avg']}ms (LoadRunner)")
            print(f"  error_rate:        {metrics['error_rate']}% (LoadRunner)")
            print(f"  throughput:        {metrics['throughput']} req/min (LoadRunner)")

        # ── CPU ──
        cpu, src = self._cpu_mem(
            "cpu", self.cpu_metric, "com.dynatrace.builtin:host.cpu.usage", 5.0)
        metrics["cpu_avg"] = cpu
        print(f"  cpu_avg:           {cpu}% ({src})")

        # ── Memory ──
        mem, src = self._cpu_mem(
            "memory", self.mem_metric, "com.dynatrace.builtin:host.mem.usage", 60.0)
        metrics["memory_avg"] = mem
        print(f"  memory_avg:        {mem}% ({src})")

        # ── Service response time (best-effort) ──
        try:
            rt = self._query_v2_metric("builtin:service.response.time")
            if rt is not None:
                metrics["dt_response_time_ms"] = round(rt / 1000, 2)
                print(f"  dt_response_time:  {metrics['dt_response_time_ms']}ms (Dynatrace v2)")
        except Exception:
            pass

        # ── Entities: services + pods ──
        metrics["service_count"] = self._count_entities("type(SERVICE)", 20)
        print(f"  service_count:     {metrics['service_count']} (Dynatrace)")
        metrics["pod_count"] = self._count_entities("type(CLOUD_APPLICATION_INSTANCE)", 100)
        print(f"  pod_count:         {metrics['pod_count']} (Dynatrace)")

        # ── Problems ──
        metrics["active_problems"] = self._problem_count()
        print(f"  active_problems:   {metrics['active_problems']} (Dynatrace)")

        print(f"  Total: {len(metrics)} metrics collected")
        return metrics

    def _count_entities(self, entity_selector: str, page_size: int) -> int:
        try:
            resp = requests.get(
                f"{self.url}/api/v2/entities",
                headers=self.headers,
                params={"entitySelector": entity_selector, "pageSize": page_size},
                timeout=30,
            )
            if resp.status_code == 200:
                return len(resp.json().get("entities", []))
        except Exception:
            pass
        return 0

    def _problem_count(self) -> int:
        try:
            resp = requests.get(
                f"{self.url}/api/v2/problems",
                headers=self.headers,
                params={"from": "now-30m", "pageSize": 10},
                timeout=30,
            )
            if resp.status_code == 200:
                return len(resp.json().get("problems", []))
        except Exception:
            pass
        return 0

    def collect_jvm_metrics(self) -> dict:
        jvm = {"oom_detected": False, "oom_count": 0}

        heap = self._query_v1_timeseries("com.dynatrace.builtin:tech.jvm.memory.heap.used")
        if heap is not None:
            jvm["jvm_heap_used_mb"] = round(heap / 1024 / 1024, 2)
            print(f"  jvm_heap: {jvm['jvm_heap_used_mb']}MB (Dynatrace v1)")

        gc = self._query_v1_timeseries("com.dynatrace.builtin:tech.jvm.gc.suspensiontime")
        if gc is not None:
            jvm["gc_suspension_ms"] = gc
            print(f"  gc_suspension: {gc}ms (Dynatrace v1)")

        threads = self._query_v1_timeseries("com.dynatrace.builtin:tech.jvm.threads")
        if threads is not None:
            jvm["thread_count"] = threads

        try:
            resp = requests.get(
                f"{self.url}/api/v2/problems",
                headers=self.headers,
                params={"from": "now-30m", "pageSize": 10},
                timeout=30,
            )
            if resp.status_code == 200:
                problems = resp.json().get("problems", [])
                oom = [p for p in problems if "OutOfMemory" in p.get("title", "")]
                jvm["oom_detected"] = len(oom) > 0
                jvm["oom_count"] = len(oom)
        except Exception:
            pass

        return jvm

    def collect_detailed_on_regression(self) -> dict:
        print("\n  Pulling detailed Dynatrace metrics...")
        detailed = {}

        try:
            resp = requests.get(
                f"{self.url}/api/v2/problems",
                headers=self.headers,
                params={"from": "now-30m", "pageSize": 10},
                timeout=30,
            )
            problems = resp.json().get("problems", []) if resp.status_code == 200 else []
            detailed["active_problems"] = [
                {"title": p.get("title", ""), "severity": p.get("severityLevel", "")}
                for p in problems
            ]
            print(f"  Active problems: {len(problems)}")
        except Exception:
            detailed["active_problems"] = []

        try:
            resp = requests.get(
                f"{self.url}/api/v2/entities",
                headers=self.headers,
                params={"entitySelector": "type(SERVICE)", "pageSize": 20},
                timeout=30,
            )
            entities = resp.json().get("entities", []) if resp.status_code == 200 else []
            detailed["affected_services"] = [e.get("displayName", "") for e in entities]
            print(f"  Affected services: {len(entities)}")
        except Exception:
            detailed["affected_services"] = []

        detailed["failed_requests_total"] = self._lr_results.get("failed_requests", 0)
        return detailed

    def collect_custom_metrics(self) -> dict:
        """
        Read custom metrics that were pushed via metrics.ingest.
        NOTE: reading them back STILL needs metrics.read -- ingest only lets you
        write. So this is not a way around the read-scope requirement.
        """
        print("  Querying custom metrics (pushed by services)...")
        custom = {}

        custom_metric_map = {
            "cpu_avg": "custom.perf.cpu_usage_pct",
            "memory_avg": "custom.perf.memory_usage_pct",
            "heap_used_mb": "custom.perf.heap_used_mb",
            "response_time_ms": "custom.perf.response_time_ms",
            "error_count": "custom.perf.error_count",
        }

        for key, metric in custom_metric_map.items():
            try:
                val = self._query_v2_metric(metric, aggregation="avg")
                if val is not None:
                    custom[key] = val
                    print(f"  {key}: {custom[key]} (custom metric)")
            except Exception:
                pass

        return custom
