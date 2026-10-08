import os
import logging
import google.cloud.logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.tools.bigquery import BigQueryToolset

from app.utils import get_latest_refresh_date, load_nl2sql_with_few_shot_prompt

load_dotenv()

# Initialize Cloud Logging
try:
    client = google.cloud.logging.Client()
    handler = CloudLoggingHandler(client)
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)
    logging.info("Cloud Logging initialized for Google Trends Analyst Agent")
    handler.close()
except Exception as e:
    logging.warning(f"Could not initialize Cloud Logging: {e}")

# Retrieve the latest partition refresh_date
latest_refresh_date = get_latest_refresh_date()
if not latest_refresh_date:
    latest_refresh_date = "2026-10-07"
    logging.warning(f"Using fallback refresh date: {latest_refresh_date}")
else:
    logging.info(f"Retrieved latest refresh date: {latest_refresh_date}")

# Render system instructions using Jinja2 prompt template
instruction = load_nl2sql_with_few_shot_prompt(refresh_date_value=latest_refresh_date)

# Define BigQuery Trends Analyst Agent
root_agent = Agent(
    name="google_trends_analyst_munozhernandez",
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    description="BigQuery SQL expert agent designed to answer natural language questions about top trending and rising international search terms from Google Trends.",
    instruction=instruction,
    tools=[BigQueryToolset()],
)

app = App(root_agent=root_agent, name="app")
