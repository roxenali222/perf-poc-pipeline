# Performance Testing AI Pipeline — POC

## Architecture
```
LoadRunner (Journey 1 + Journey 2)
    ↓
Dynatrace Metrics (services, pods, problems)
    ↓
Regression Agent (compare vs baseline)
    ↓ (if regression)
Dynatrace Detail Pull (PurePath, problems)
    ↓
RCA Agent (Azure OpenAI GPT-5.6-sol)
    ↓
Output: HTML Report + Jira + Teams
```

## Quick Start
```bash
pip install -r requirements.txt
python main.py
```

## Folder Structure
```
poc-local/
├── main.py                    ← Entry point
├── config.py                  ← Loads .env
├── .env                       ← All credentials (pre-filled)
├── baseline.json              ← Baseline metrics
├── requirements.txt
├── agents/
│   ├── regression_agent.py    ← Baseline comparison
│   └── rca_agent.py           ← Azure OpenAI GPT-5.6-sol RCA
├── collectors/
│   ├── dynatrace.py           ← Dynatrace API
│   └── pagespeed.py           ← PageSpeed Insights
├── loadrunner/
│   ├── journey1_login_browse.py   ← Login & Browse journey
│   ├── journey2_search_checkout.py ← Search & Checkout journey
│   └── trigger.py             ← Runs both journeys
└── output/
    ├── notifier.py            ← Teams + Jira notifications
    ├── report.py              ← HTML report generator
    └── report.html            ← Generated report
```

## AKS Services
```
Product Service: http://172.210.93.51
User Service:    http://20.81.60.76
Order Service:   http://57.152.89.143
```

## Credentials (pre-configured)
```
Dynatrace:    https://isz24970.live.dynatrace.com
Azure OpenAI: gpt-5.6-sol (saifkhalid-5480-resource)
Jira:         https://saifullakhalid.atlassian.net (reactivate needed)
Teams:        Webhook URL pending from client
```

## Production Integration (CircleCI)
Add to .circleci/config.yml:
```yaml
- run:
    name: Run Performance Pipeline
    command: |
      pip install -r requirements.txt
      python main.py
```

## LoadRunner Production Integration
Edit loadrunner/trigger.py:
- Option 1: LRE REST API → use _trigger_lr_enterprise()
- Option 2: Results file → use _parse_lr_results()

## Pending
- Teams webhook URL (from client)
- Jira reactivation
- metrics.read scope for CPU/Memory (DevOps needed)
