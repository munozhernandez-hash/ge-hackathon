# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import google
import google.auth
from dotenv import find_dotenv, load_dotenv
from google.cloud import bigquery
from jinja2 import Environment, FileSystemLoader

load_dotenv(find_dotenv(usecwd=True), override=True)

PROMPTS_DIR_NAME = "prompts"
PROMPT_FILE_NAME = "google_trends_nl2sql_with_few_shot.j2"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")


def load_nl2sql_with_few_shot_prompt(
    refresh_date_value: str,
    prompts_dir_name: str = PROMPTS_DIR_NAME,
    prompt_file_name: str = PROMPT_FILE_NAME,
) -> str:
    """Loads and renders the Google Trends table structure and rules template.

    Args:
        refresh_date_value: The refresh date to use in the template (YYYY-MM-DD).

    Returns:
        str: The rendered template content.
    """
    try:
        # Set up Jinja environment
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, prompts_dir_name)
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(prompt_file_name)

        # Prepare template variables
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or GOOGLE_CLOUD_PROJECT
        template_vars = {
            "refresh_date_value": refresh_date_value,
            "GOOGLE_CLOUD_PROJECT": project_id,
        }

        # Render the template
        return template.render(**template_vars)

    except Exception as e:
        print(f"Error loading table structure template: {str(e)}")
        raise


def get_latest_refresh_date(
    table_name: str = "bigquery-public-data.google_trends.international_top_terms",
) -> str | None:
    """
    Retrieves the most recent 'refresh_date' from a specified BigQuery table.

    This function connects to Google BigQuery, executes a query to find the
    maximum 'refresh_date', and returns it as a formatted string. It includes
    robust error handling for authentication issues, API errors (like table
    not found), and other potential exceptions.

    Args:
        table_name (str): The full ID of the BigQuery table to query, in the
                          format 'project.dataset.table'. Defaults to the
                          Google Trends international top terms table.

    Returns:
        str | None: The latest date as a string in 'YYYY-MM-DD' format if
                    successful and a date is found. Returns None if an error
                    occurs or if the table has no 'refresh_date' entries.

    Raises:
        This function catches exceptions and prints error messages instead of
        raising them, returning None on failure.
    """
    try:
        bq_client = setup_bq_connection()

        # Use an f-string to correctly insert the table_name into the query
        query = f"""
            SELECT MAX(refresh_date) AS latest_date
            FROM `{table_name}`
        """

        query_job = bq_client.query(query)
        results = query_job.result()

        # Safely iterate over the single result row
        for row in results:
            # Check if a date was actually found (handles empty tables)
            if row and row.latest_date:
                latest_refresh_date = row.latest_date.strftime("%Y-%m-%d")
                print(f"   ...found latest refresh_date: {latest_refresh_date}")
                return latest_refresh_date

        print(f"   ...could not find a 'refresh_date' in table '{table_name}'.")
        return None

    except google.auth.exceptions.RefreshError as e:
        print(f"❌ Authentication error: {e}")
        print("   Your credentials may have expired. Try re-authenticating.")
        return None

    except google.api_core.exceptions.NotFound as e:
        print(
            f"❌ Table not found: The table '{table_name}' does not exist or you lack permission to view it."
        )
        return None

    except google.api_core.exceptions.GoogleAPICallError as e:
        print(f"❌ A Google Cloud API error occurred: {e}")
        return None

    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return None


def setup_bq_connection():
    try:
        # Load environment variables from .env file
        load_dotenv(find_dotenv(usecwd=True), override=True)

        # Get project ID from environment variables
        # Use default credentials to get the project ID if not set
        try:
            _, project_id = google.auth.default()
        except google.auth.exceptions.DefaultCredentialsError:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

        if not project_id:
            raise ValueError(
                "GCP Project ID is not set. Please set the GOOGLE_CLOUD_PROJECT environment "
                "variable or login with `gcloud auth application-default login`."
            )

        # Initialize BigQuery client
        bq_client = bigquery.Client(project=project_id)

        return bq_client

    except Exception as e:
        print(f"Error: {str(e)}")
