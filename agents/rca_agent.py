"""
RCA Agent — Root Cause Analysis using Azure OpenAI
Supports both Azure OpenAI and Azure AI Services endpoints
"""
import json
import requests


class RCAAgent:

    def __init__(self, endpoint: str, api_key: str, deployment: str = "gpt-5.6-sol"):
        self.endpoint = (endpoint or "").rstrip("/")
        self.api_key = api_key
        self.deployment = deployment

    def _get_url(self) -> str:
        """Build correct API URL based on endpoint type"""
        # Azure AI Services endpoint
        if "services.ai.azure.com" in self.endpoint:
            return (
                f"{self.endpoint}/openai/deployments/{self.deployment}"
                f"/chat/completions?api-version=2024-12-01-preview"
            )
        # Standard Azure OpenAI endpoint
        return (
            f"{self.endpoint}/openai/deployments/{self.deployment}"
            f"/chat/completions?api-version=2024-02-01"
        )

    def _build_prompt(self, metrics: dict, regression_context: dict, target_url: str) -> str:
        reasons = regression_context.get("reasons", [])
        delta = regression_context.get("metrics_delta", {})
        detailed = regression_context.get("detailed_metrics", {})
        jvm = regression_context.get("jvm_metrics", {})

        prompt = f"""You are a senior performance engineering expert.

Application URL: {target_url}

REGRESSION DETECTED:
Severity: {regression_context.get('severity', 'unknown').upper()}

Regression Reasons:
{chr(10).join(f"- {r}" for r in reasons)}

Metrics Comparison (baseline vs current):
{json.dumps(delta, indent=2)}

Current Metrics:
{json.dumps(metrics, indent=2)}
"""
        if detailed.get("active_problems"):
            prompt += f"\nActive Dynatrace Problems:\n{json.dumps(detailed['active_problems'], indent=2)}"

        if detailed.get("slowest_traces"):
            prompt += f"\nSlowest PurePath Traces:\n{json.dumps(detailed['slowest_traces'], indent=2)}"

        if jvm.get("oom_detected"):
            prompt += f"\n⚠️ OOM DETECTED: {jvm.get('oom_count')} incidents!"

        if detailed.get("affected_services"):
            prompt += f"\nAffected Services: {', '.join(detailed['affected_services'])}"

        prompt += """

Provide root cause analysis in JSON format only (no markdown):
{
  "summary": "2-3 sentence summary of the regression",
  "likely_causes": ["cause1", "cause2", "cause3"],
  "recommended_actions": ["action1", "action2", "action3"],
  "metrics_to_monitor": ["metric1", "metric2"],
  "severity_assessment": "brief severity explanation"
}"""
        return prompt

    def analyze(self, metrics: dict, regression_context: dict, target_url: str) -> dict:
        if not self.api_key or not self.endpoint:
            print("  Azure OpenAI not configured — using mock RCA")
            return self._mock_rca(regression_context)

        try:
            url = self._get_url()
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior performance engineer. Respond with valid JSON only, no markdown."
                    },
                    {
                        "role": "user",
                        "content": self._build_prompt(metrics, regression_context, target_url)
                    }
                ],
                "max_completion_tokens": 1000
            }

            print(f"  Calling Azure OpenAI: {self.deployment}")
            resp = requests.post(url, headers=headers, json=payload, timeout=60)

            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                content = content.strip()
                # Remove markdown if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()
                result = json.loads(content)
                print("  ✅ Azure OpenAI RCA complete!")
                return result
            else:
                print(f"  Azure OpenAI error {resp.status_code}: {resp.text[:300]}")
                return self._mock_rca(regression_context)

        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            return self._mock_rca(regression_context)
        except Exception as e:
            print(f"  RCA error: {e}")
            return self._mock_rca(regression_context)

    def _mock_rca(self, regression_context: dict) -> dict:
        reasons = regression_context.get("reasons", [])
        return {
            "summary": f"Performance regression detected with {len(reasons)} metric(s) degraded. "
                      f"Response time and throughput show significant degradation compared to baseline.",
            "likely_causes": [
                "AKS cluster resource constraints causing increased latency",
                "Network latency between local machine and AKS services",
                "Application cold start after pod restart",
                "Insufficient node resources for current load"
            ],
            "recommended_actions": [
                "Check AKS pod resource limits and requests",
                "Review Dynatrace PurePath traces for bottlenecks",
                "Consider scaling AKS node count",
                "Review application logs for errors or warnings"
            ],
            "metrics_to_monitor": [
                "response_time_avg",
                "error_rate",
                "throughput",
                "pod_count"
            ],
            "severity_assessment": f"HIGH severity regression — response time degraded significantly from baseline"
        }
