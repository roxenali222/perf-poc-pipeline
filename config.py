"""
Configuration — loads from .env file
"""
import os
from dotenv import load_dotenv

load_dotenv()

config = {
    # Azure OpenAI
    "AZURE_OPENAI_ENDPOINT":   os.getenv("AZURE_OPENAI_ENDPOINT"),
    "AZURE_OPENAI_KEY":        os.getenv("AZURE_OPENAI_KEY"),
    "AZURE_OPENAI_DEPLOYMENT": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),

    # Dynatrace
    "DYNATRACE_URL":             os.getenv("DYNATRACE_URL"),
    "DYNATRACE_TOKEN":           os.getenv("DYNATRACE_TOKEN"),
    "DYNATRACE_ENTITY_SELECTOR": os.getenv("DYNATRACE_ENTITY_SELECTOR", "type(SERVICE)"),

    # Target App
    "TARGET_URL": os.getenv("TARGET_URL", "http://172.210.93.51"),

    # PageSpeed
    "PAGESPEED_API_KEY": os.getenv("PAGESPEED_API_KEY", ""),

    # Regression
    "BASELINE_FILE":            os.getenv("BASELINE_FILE", "baseline.json"),
    "REGRESSION_THRESHOLD_PCT": int(os.getenv("REGRESSION_THRESHOLD_PCT", "15")),

    # Teams
    "TEAMS_WEBHOOK_URL": os.getenv("TEAMS_WEBHOOK_URL", ""),

    # Jira
    "JIRA_URL":         os.getenv("JIRA_URL"),
    "JIRA_TOKEN":       os.getenv("JIRA_TOKEN"),
    "JIRA_EMAIL":       os.getenv("JIRA_EMAIL"),
    "JIRA_PROJECT_KEY": os.getenv("JIRA_PROJECT_KEY", "KAN"),
}
