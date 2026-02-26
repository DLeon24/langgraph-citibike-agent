"""
Tool: Run SQL Query (BigQuery)
Executes SQL queries against BigQuery and returns a markdown table,
a no-results message, or an error message.
"""

import os
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from google.cloud.bigquery import dbapi
from langchain_core.tools import tool
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ============================================
# BIGQUERY CONFIGURATION
# ============================================
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
DB_URI = os.getenv(
    "BIGQUERY_DB_URI", "bigquery://bigquery-public-data/new_york_citibike"
)

if not GOOGLE_CLOUD_PROJECT:
    raise ValueError(
        "❌ Missing BigQuery variable in .env\n" "Required: GOOGLE_CLOUD_PROJECT"
    )

if not DB_URI:
    raise ValueError(
        "❌ Missing BigQuery variable in .env\n" "Required: BIGQUERY_DB_URI"
    )

_engine: Engine | None = None


# ============================================
# EXPORTABLE TOOL
# ============================================
@tool
def run_sql_query(query: str) -> str:
    """
    Runs a SQL query in BigQuery and returns a markdown table.

    Args:
        query: Full SQL query to execute using the BigQuery SQL dialect.

    Returns:
        Query result as a markdown table, a no-results message,
        or an error message.
    """
    try:
        return _execute_sql_query(query)
    except Exception as e:
        return f"Error running query: {e}"


# ============================================
# INTERNAL FUNCTIONS
# ============================================
def _execute_sql_query(query: str) -> str:
    """
    Executes SQL and returns query output as a user-readable string.

    Returns:
        A markdown table when rows are found, otherwise a no-results message.
    """
    engine = _get_engine()

    with engine.connect() as connection:
        result_proxy = connection.execute(text(query))
        df = pd.DataFrame(result_proxy.fetchall(), columns=result_proxy.keys())

    if df.empty:
        return "The query executed successfully, but returned no results."

    return df.to_markdown(index=False)


def _get_engine() -> Engine:
    """
    Returns the SQLAlchemy engine with lazy initialization.
    This avoids credential errors at module import time.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(DB_URI, creator=_get_bigquery_connection)
    return _engine


def _get_bigquery_connection():
    """
    Creates a DB-API BigQuery connection.
    Supports credentials from GOOGLE_APPLICATION_CREDENTIALS or ADC.

    Raises:
        FileNotFoundError: If GOOGLE_APPLICATION_CREDENTIALS points
        to a non-existent file.
    """
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if credentials_path:
        credentials_path = _resolve_credentials_path(credentials_path)
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Credentials file not found: {credentials_path}\n"
                "Verify that GOOGLE_APPLICATION_CREDENTIALS points to a valid file."
            )
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

    client = bigquery.Client(project=GOOGLE_CLOUD_PROJECT)
    return dbapi.connect(client=client)


def _resolve_credentials_path(credentials_path: str) -> str:
    """Resolves a credentials path to absolute path when it is relative."""
    if os.path.isabs(credentials_path):
        return credentials_path

    project_root = Path(__file__).parent.parent
    return str((project_root / credentials_path).resolve())
