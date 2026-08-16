# ⚡ Performance Testing AI Pipeline — POC

An automated, end-to-end performance regression testing pipeline that combines synthetic load testing, live observability data, and AI-driven root cause analysis — all in one local, runnable system.

Built to catch performance regressions **before they reach users**, and explain *why* they happened, not just *that* they happened.

---

## 🧠 What It Does

1. **Simulates real user journeys** (Login & Browse, Search & Checkout) against a live application
2. **Pulls live infrastructure metrics** — CPU, Memory, active services, pod count, and open problems — directly from the **Dynatrace Metrics v2 API**
3. **Compares results against a stored baseline** to automatically detect performance regressions (response time, error rate, throughput, resource usage)
4. **When a regression is detected**, calls **Azure OpenAI (GPT)** to generate a full root cause analysis — likely causes, affected components, and specific recommended actions
5. **Outputs a polished HTML report**, with optional **Microsoft Teams** alerts and **Jira** ticket creation

---

## 🏗️ Architecture

```
LoadRunner (Journey 1 + Journey 2)
        ↓
Dynatrace Metrics (services, pods, problems)
        ↓
Regression Agent (compare vs baseline)
        ↓ (if regression detected)
Dynatrace Detail Pull (PurePath, problems)
        ↓
RCA Agent (Azure OpenAI)
        ↓
Output: HTML Report + Jira Ticket + Teams Alert
```

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python main.py
```

First run seeds the baseline — run it a second time to see regression detection in action.

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in your own values:

```
DYNATRACE_URL=
DYNATRACE_TOKEN=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_KEY=
TARGET_URL=
```

> No credentials are committed to this repo — configure your own environment via `.env`.

---

## 📁 Folder Structure

```
poc-local/
├── main.py                          ← Entry point
├── config.py                        ← Loads environment config
├── baseline.json                    ← Stored performance baseline
├── requirements.txt
├── agents/
│   ├── regression_agent.py          ← Baseline comparison logic
│   └── rca_agent.py                 ← Azure OpenAI root cause analysis
├── collectors/
│   ├── dynatrace.py                 ← Dynatrace Metrics/Entities/Problems API
│   └── pagespeed.py                 ← PageSpeed Insights integration
├── loadrunner/
│   ├── journey1_login_browse.py     ← User journey 1
│   ├── journey2_search_checkout.py  ← User journey 2
│   └── trigger.py                   ← Runs both journeys
└── output/
    ├── notifier.py                  ← Teams + Jira notifications
    ├── report.py                    ← HTML report generator
    └── report.html                  ← Generated report
```

---

## 🔌 Integrations

- **Dynatrace** — Metrics v2, Entities, and Problems APIs for live infrastructure data
- **Azure OpenAI** — GPT-powered root cause analysis on regression detection
- **Microsoft Teams** — optional webhook alerts
- **Jira** — optional automatic ticket creation on regression
- **CircleCI** — drop-in CI step to run the pipeline on every deploy:

```yaml
- run:
    name: Run Performance Pipeline
    command: |
      pip install -r requirements.txt
      python main.py
```

---

## 🛠️ Tech Stack

`Python` · `Dynatrace API` · `Azure OpenAI` · `Jira REST API` · `Microsoft Teams Webhooks`

---

## 📌 Status

This is a working local POC. Production LoadRunner Enterprise integration and live application endpoints are configured per-environment via `.env` and are not included in this repository.