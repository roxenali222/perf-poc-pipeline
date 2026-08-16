"""
POC Local — Performance Testing AI Pipeline
============================================
Flow:
  1. Run LoadRunner journeys (Login&Browse + Search&Checkout)
  2. Collect Dynatrace metrics (CPU, Memory, JVM, GC, OOM, Response time)
  3. Compare vs baseline → detect regression
  4. If regression → pull detailed Dynatrace metrics (PurePath, problems)
  5. Run RCA via Azure OpenAI
  6. Output: HTML report + Jira ticket + Teams alert

Run: python main.py
"""
import json
import time
from datetime import datetime

from config import config
from collectors.dynatrace import DynatraceCollector
from collectors.pagespeed import PageSpeedCollector
from loadrunner.trigger import LoadRunnerTrigger
from agents.regression_agent import RegressionAgent
from agents.rca_agent import RCAAgent
from output.notifier import Notifier
from output.report import generate_report


def run_pipeline():
    print("\n" + "="*60)
    print("  PERFORMANCE TESTING AI PIPELINE — LOCAL POC")
    print("="*60)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Product: {config.get('PRODUCT_SERVICE_URL', config['TARGET_URL'])}")
    print(f"  User:    {config.get('USER_SERVICE_URL', 'N/A')}")
    print(f"  Order:   {config.get('ORDER_SERVICE_URL', 'N/A')}")
    print("="*60 + "\n")

    results = {
        "timestamp": datetime.now().isoformat(),
        "loadrunner": {},
        "metrics": {},
        "jvm_metrics": {},
        "detailed_metrics": {},
        "regression": {},
        "rca": {},
    }

    # ──────────────────────────────────────────
    # STEP 1 — Run LoadRunner Journeys
    # ──────────────────────────────────────────
    print("STEP 1: Running LoadRunner Test Journeys...")
    print("  Journey 1: Login & Browse")
    print("  Journey 2: Search & Checkout")

    lr = LoadRunnerTrigger(
        base_url=config.get("TARGET_URL", "http://172.210.93.51"),
        duration_seconds=60,
        vus=5
    )
    lr_results = lr.run()
    results["loadrunner"] = lr_results

    # Wait for Dynatrace to process metrics
    print("\n  Waiting 30 seconds for Dynatrace to process metrics...")
    time.sleep(30)

    # ──────────────────────────────────────────
    # STEP 2 — Collect Dynatrace Metrics
    # ──────────────────────────────────────────
    print("\nSTEP 2: Collecting Dynatrace Metrics...")
    dynatrace = DynatraceCollector(
        url=config["DYNATRACE_URL"],
        token=config["DYNATRACE_TOKEN"],
        entity_selector=config.get("DYNATRACE_ENTITY_SELECTOR", "type(SERVICE)")
    )

    # Basic metrics
    dynatrace.set_lr_results(lr_results)
    dynatrace_metrics = dynatrace.collect()
    results["metrics"]["dynatrace"] = dynatrace_metrics

    print(f"\n  Basic Metrics:")
    print(f"  CPU:           {dynatrace_metrics.get('cpu_avg')}%")
    print(f"  Memory:        {dynatrace_metrics.get('memory_avg')}%")
    print(f"  Response Time: {dynatrace_metrics.get('response_time_avg')}ms")
    print(f"  Error Rate:    {dynatrace_metrics.get('error_rate')}%")
    print(f"  Throughput:    {dynatrace_metrics.get('throughput')} req/min")

    # JVM Metrics (Spring Boot)
    print(f"\n  Collecting JVM Metrics (Spring Boot)...")
    jvm_metrics = dynatrace.collect_jvm_metrics()
    results["jvm_metrics"] = jvm_metrics

    if jvm_metrics:
        print(f"  JVM Heap:      {jvm_metrics.get('jvm_heap_used_mb', 'N/A')}MB")
        print(f"  GC Suspension: {jvm_metrics.get('gc_suspension_ms', 'N/A')}ms")
        print(f"  GC Count:      {jvm_metrics.get('gc_count', 'N/A')}")
        print(f"  Threads:       {jvm_metrics.get('thread_count', 'N/A')}")
        print(f"  OOM Detected:  {jvm_metrics.get('oom_detected', False)}")
    else:
        print("  No JVM metrics (Node.js services — JVM only for Spring Boot)")

    # Combine all metrics for regression
    all_metrics = {
        **dynatrace_metrics,
        **jvm_metrics,
        "lr_avg_response_ms": lr_results.get("avg_response_time_ms", 0),
        "lr_p90_response_ms": lr_results.get("p90_response_time_ms", 0),
        "lr_error_rate_pct":  lr_results.get("error_rate_pct", 0),
        "lr_throughput":      lr_results.get("throughput_per_min", 0),
    }
    results["metrics"]["all"] = all_metrics

    # ──────────────────────────────────────────
    # STEP 3 — Regression Detection
    # ──────────────────────────────────────────
    print("\nSTEP 3: Running Regression Detection...")
    regression = RegressionAgent(
        baseline_file=config["BASELINE_FILE"],
        threshold_pct=config["REGRESSION_THRESHOLD_PCT"]
    )
    regression_result = regression.evaluate(all_metrics)
    results["regression"] = regression_result

    if regression_result.get("baseline_seeded"):
        print("  First run — baseline seeded!")
        print("  Run pipeline again to detect regression.")
    elif regression_result["regression"]:
        print(f"\n  ❌ REGRESSION DETECTED!")
        print(f"  Severity: {regression_result['severity'].upper()}")
        for reason in regression_result["reasons"]:
            print(f"     → {reason}")
    else:
        print("  ✅ No regression — all metrics within threshold")

    # ──────────────────────────────────────────
    # STEP 4 — Detailed Dynatrace (if regression)
    # ──────────────────────────────────────────
    if regression_result.get("regression"):
        print("\nSTEP 4: Pulling Detailed Dynatrace Metrics...")
        print("  → PurePath traces")
        print("  → Active problems")
        print("  → Affected services")
        print("  → Failed requests")

        detailed = dynatrace.collect_detailed_on_regression()
        results["detailed_metrics"] = detailed

        print(f"\n  Failed Requests:  {detailed.get('failed_requests_total', 0)}")
        print(f"  Active Problems:  {len(detailed.get('active_problems', []))}")
        print(f"  PurePath Traces:  {len(detailed.get('slowest_traces', []))}")
        print(f"  Services:         {len(detailed.get('affected_services', []))}")

        if detailed.get("slowest_traces"):
            print("\n  Top Slow Traces:")
            for t in detailed["slowest_traces"][:3]:
                failed_tag = "❌ FAILED" if t.get("failed") else "✅"
                print(f"     {failed_tag} {t.get('name', 'N/A')} — {t.get('duration_ms')}ms")

        if detailed.get("active_problems"):
            print("\n  Active Problems:")
            for p in detailed["active_problems"][:3]:
                print(f"     ⚠️  {p.get('title')} [{p.get('severity')}]")
    else:
        print("\nSTEP 4: Skipped (no regression)")

    # ──────────────────────────────────────────
    # STEP 5 — RCA via Azure OpenAI
    # ──────────────────────────────────────────
    if regression_result.get("regression"):
        print("\nSTEP 5: Running AI Root Cause Analysis...")
        regression_result["detailed_metrics"] = results.get("detailed_metrics", {})
        regression_result["jvm_metrics"] = jvm_metrics

        rca = RCAAgent(
            endpoint=config["AZURE_OPENAI_ENDPOINT"],
            api_key=config["AZURE_OPENAI_KEY"],
            deployment=config["AZURE_OPENAI_DEPLOYMENT"]
        )
        rca_result = rca.analyze(all_metrics, regression_result, config["TARGET_URL"])
        results["rca"] = rca_result

        print(f"\n  Summary: {rca_result.get('summary', 'N/A')}")
        print(f"\n  Likely Causes:")
        for cause in rca_result.get("likely_causes", []):
            print(f"     → {cause}")
        print(f"\n  Recommended Actions:")
        for action in rca_result.get("recommended_actions", []):
            print(f"     → {action}")
    else:
        print("\nSTEP 5: RCA skipped (no regression)")
        results["rca"] = {"skipped": True}

    # ──────────────────────────────────────────
    # STEP 6 — Output
    # ──────────────────────────────────────────
    print("\nSTEP 6: Generating Output...")

    report_path = generate_report(results)
    print(f"  ✅ HTML Report: {report_path}")

    if regression_result.get("regression"):
        notifier = Notifier(
            teams_webhook=config.get("TEAMS_WEBHOOK_URL", ""),
            jira_url=config.get("JIRA_URL", ""),
            jira_token=config.get("JIRA_TOKEN", ""),
            jira_email=config.get("JIRA_EMAIL", ""),
            jira_project=config.get("JIRA_PROJECT_KEY", "KAN")
        )
        notifier.notify(results)

    # ──────────────────────────────────────────
    # FINAL SUMMARY
    # ──────────────────────────────────────────
    print("\n" + "="*60)
    print("  PIPELINE COMPLETE")
    print("="*60)

    if regression_result.get("baseline_seeded"):
        print("  Status:    BASELINE SEEDED")
        print("  Next Step: Run again to detect regression")
    else:
        status = "❌ REGRESSION DETECTED" if regression_result["regression"] else "✅ PASSED"
        print(f"  Status:    {status}")
        if regression_result["regression"]:
            print(f"  Severity:  {regression_result['severity'].upper()}")

    print(f"\n  LoadRunner Results:")
    print(f"  Iterations: {lr_results.get('iterations', 1)}")
    print(f"  Requests:   {lr_results.get('total_requests')}")
    print(f"  Avg RT:     {lr_results.get('avg_response_time_ms')}ms")
    print(f"  P90 RT:     {lr_results.get('p90_response_time_ms')}ms")
    print(f"  Throughput: {lr_results.get('throughput_per_min')} req/min")
    print(f"  Error Rate: {lr_results.get('error_rate_pct')}%")
    print(f"\n  Report:    {report_path}")
    print("="*60 + "\n")

    return results


if __name__ == "__main__":
    run_pipeline()
