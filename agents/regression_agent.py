"""
Regression Agent — Compares current metrics vs baseline.json
"""
import json
import os
from datetime import datetime

METRIC_DIRECTION = {
    "cpu_avg":           "lower_is_better",
    "memory_avg":        "lower_is_better",
    "response_time_avg": "lower_is_better",
    "error_rate":        "lower_is_better",
    "throughput":        "higher_is_better",
    "lcp":               "lower_is_better",
    "cls":               "lower_is_better",
    "tti":               "lower_is_better",
    "fcp":               "lower_is_better",
    "performance_score": "higher_is_better",
}

THRESHOLDS = {
    "cpu_avg": 20, "memory_avg": 20, "response_time_avg": 15,
    "error_rate": 10, "throughput": 20, "lcp": 15,
    "cls": 20, "tti": 15, "fcp": 15, "performance_score": 10,
}


class RegressionAgent:

    def __init__(self, baseline_file: str, threshold_pct: int = 15):
        self.baseline_file = baseline_file
        self.default_threshold = threshold_pct

    def _load_baseline(self):
        if not os.path.exists(self.baseline_file):
            return None
        with open(self.baseline_file, "r") as f:
            data = json.load(f)
        return data.get("metrics", {})

    def _save_baseline(self, metrics: dict):
        baseline = {"created_at": datetime.now().isoformat(), "metrics": metrics}
        with open(self.baseline_file, "w") as f:
            json.dump(baseline, f, indent=2)
        print(f"  Baseline saved to {self.baseline_file}")

    def evaluate(self, current_metrics: dict) -> dict:
        baseline = self._load_baseline()

        if not baseline:
            print("  No baseline found — seeding baseline")
            self._save_baseline(current_metrics)
            return {
                "regression": False, "baseline_seeded": True,
                "severity": None, "reasons": [], "metrics_delta": {},
                "current_metrics": current_metrics, "baseline_metrics": current_metrics
            }

        reasons = []
        metrics_delta = {}
        regression_count = 0
        high_severity = False

        for metric, current_val in current_metrics.items():
            baseline_val = baseline.get(metric)
            if baseline_val is None or baseline_val == 0:
                continue

            direction = METRIC_DIRECTION.get(metric, "lower_is_better")
            threshold = THRESHOLDS.get(metric, self.default_threshold)
            delta = current_val - baseline_val
            delta_pct = (delta / baseline_val) * 100

            metrics_delta[metric] = {
                "baseline": baseline_val, "current": current_val,
                "delta": round(delta, 4), "delta_pct": round(delta_pct, 2)
            }

            is_regression = False
            if direction == "lower_is_better" and delta_pct > threshold:
                is_regression = True
            elif direction == "higher_is_better" and delta_pct < -threshold:
                is_regression = True

            if is_regression:
                regression_count += 1
                reasons.append(
                    f"{metric} regressed ({direction}): "
                    f"{round(baseline_val, 2)} -> {round(current_val, 2)} "
                    f"({'+' if delta_pct > 0 else ''}{round(delta_pct, 1)}%)"
                )
                if abs(delta_pct) > 50:
                    high_severity = True

        severity = None
        if regression_count > 0:
            if high_severity or regression_count >= 4:
                severity = "high"
            elif regression_count >= 2:
                severity = "medium"
            else:
                severity = "low"

        return {
            "regression": regression_count > 0, "severity": severity,
            "reasons": reasons, "metrics_delta": metrics_delta,
            "current_metrics": current_metrics, "baseline_metrics": baseline
        }
