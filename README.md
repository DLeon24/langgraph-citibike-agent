# LangGraph CitiBike SQL Agent

Technical documentation for the CitiBike NYC SQL Analyst Agent: a LangGraph-based AI agent that converts natural language questions into BigQuery SQL and answers them using the public CitiBike NYC dataset.

---

## Table of Contents

- [Technical Description](#technical-description)
- [Architecture Overview](#architecture-overview)
- [Technologies and Cloud Services](#technologies-and-cloud-services)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Security and Best Practices](#security-and-best-practices)

---

## Technical Description

This project is an **NL-to-SQL agent** that answers natural language questions about CitiBike NYC trip data stored in Google BigQuery. The agent:

- **Converts** user questions in natural language into BigQuery SQL via OpenAI GPT-4o
- **Executes** SQL through a LangChain tool (`run_sql_query`) that connects to BigQuery
- **Iterates** automatically when SQL errors occur—the LLM analyzes the error, fixes the query, and retries
- **Responds** in friendly, natural language with the results formatted as markdown tables

The application is exposed via a **Streamlit** chat UI and can be run locally, in Docker, or with **LangGraph Studio** (via `langgraph dev`) for development and debugging. Optional **LangSmith** tracing provides observability for agent runs.

- **Data source**: BigQuery public dataset `bigquery-public-data.new_york_citibike.citibike_trips`
- **No microservices or event queues** — synchronous request/response flow

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    Streamlit UI (main.py)                         │
│                                                                  │
│  Chat interface • Example questions • Session state (UI only)    │
└──────────────────────┬───────────────────────────────────────────┘
                       │  run_agent(query)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                LangGraph Agent (agent.py)                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  StateGraph: agent → [tools | end] → (tools) → agent loop   │ │
│  │                                                             │ │
│  │  • agent node: call_model (LLM with tools bound)            │ │
│  │  • tools node: ToolNode([run_sql_query])                    │ │
│  │  • should_continue: route to tools or end                   │ │
│  └────────────────────────────┬────────────────────────────────┘ │
│                               │                                  │
│                               ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              OpenAI API (GPT-4o)                             │ │
│  │    NL → SQL generation  |  Error analysis  |  Final answer   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       │  run_sql_query tool
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│               BigQuery (Google Cloud)                             │
│                                                                  │
│  Dataset: bigquery-public-data.new_york_citibike                 │
│  Table: citibike_trips                                           │
│  ┌──────────────────┬─────────────────┬──────────────────────┐  │
│  │ tripduration     │ start_station_* │ end_station_*        │  │
│  │ starttime        │ bikeid          │ usertype, gender     │  │
│  │ stoptime         │ birth_year      │ customer_plan        │  │
│  └──────────────────┴─────────────────┴──────────────────────┘  │
│                                                                  │
│  Access: SQLAlchemy + sqlalchemy-bigquery + google-cloud-bigquery │
└──────────────────────────────────────────────────────────────────┘
```

**Key points:**

- **Synchronous flow** — No message queues or event-driven architecture. User sends a question; the agent processes it and returns a response.
- **Single-process deployment** — One Streamlit process runs the UI and invokes the LangGraph agent in-process.
- **Stateless per request** — No conversation memory; each question is independent. Session state in Streamlit is UI-only (chat history in the browser session).
- **Agent loop** — agent → tools → agent until the LLM produces a final answer without tool calls.

---

## Technologies and Cloud Services


| Layer               | Technology                                                                  |
| ------------------- | --------------------------------------------------------------------------- |
| Runtime             | Python 3.11 (see `Dockerfile`)                                              |
| UI                  | Streamlit (`main.py`)                                                       |
| Agent orchestration | LangGraph ≥1.0                                                              |
| LLM                 | OpenAI GPT-4o (`langchain-openai`)                                          |
| Database            | Google BigQuery (`bigquery-public-data.new_york_citibike.citibike_trips`)   |
| DB access           | SQLAlchemy + `sqlalchemy-bigquery`, `google-cloud-bigquery`                 |
| Data formatting     | pandas, tabulate (markdown output)                                          |
| Observability       | LangSmith (optional, via `LANGSMITH_`* env vars; comes with langchain-core) |
| Config              | `python-dotenv`, `.env` (see `.gitignore`)                                  |


---

## Project Structure

```
.
├── main.py                 # Streamlit chat UI entry point
├── agent.py                # LangGraph agent: graph, nodes, run_agent()
├── langgraph.json          # LangGraph Studio config (graphs.agent → agent:app)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Production container (Streamlit on port 8000)
├── build.sh                # Docker build helper (multi-arch: arm64/amd64)
├── commands.md             # Dev commands (LangGraph CLI, Docker deploy)
├── .env                    # Environment variables (not in repo; see Configuration)
├── .gitignore
├── .dockerignore           # Excludes .env, venv, *.json except langgraph.json
└── tools/
    ├── __init__.py         # Exports run_sql_query
    └── run_sql_query.py    # BigQuery SQL execution tool
```

---

## Installation & Setup

### Prerequisites

- **Python 3.11+**
- **Google Cloud project** with BigQuery access and a service account
- **OpenAI API key**
- **Docker** (optional, for containerized deployment)
- **LangGraph CLI** (optional, for LangGraph Studio development)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd langgraph-citibike-agent
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate    # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root. See [Configuration](#configuration) for the required variables.

### 5. Set Up Google Cloud Credentials

- Create a service account in your GCP project with BigQuery Data Viewer (or equivalent) role.
- Download the JSON key file.
- Place it in the project directory (e.g. `project-ai-agent-bigquery-0ac9b0b21f1d.json`) and reference it via `GOOGLE_APPLICATION_CREDENTIALS` in `.env`.

**Assumption:** The public dataset `bigquery-public-data.new_york_citibike.citibike_trips` is readable without additional project-level configuration. If your project has restricted access, you may need to enable the BigQuery API and grant access to the public dataset.

---

## Running the Application

### Streamlit (Production / Default)

```bash
streamlit run main.py
```

By default, Streamlit listens on `http://localhost:8501`. Open this URL in your browser.

To specify port and binding:

```bash
streamlit run main.py --server.port 8000 --server.address 0.0.0.0
```

### LangGraph Studio (Development)

For graph visualization and debugging:

```bash
# Install LangGraph CLI (Python 3.11 required)
pip install -U "langgraph-cli[inmem]"

# Start LangGraph dev server
langgraph dev --allow-blocking
```

### Docker

Build using the provided script:

```bash
chmod +x build.sh
./build.sh <dockerhub_user> <version> <arch>
# Example: ./build.sh myuser 1.0.0 amd64
```

Or build and run manually:

```bash
docker build -t langgraph-citibike-agent:latest .
docker run -p 8000:8000 --env-file .env -v $(pwd)/path-to-credentials.json:/app/credentials.json langgraph-citibike-agent:latest
```

**Note:** The container expects credentials. Either pass `GOOGLE_APPLICATION_CREDENTIALS` pointing to a path inside the container, or mount the JSON file and set the path accordingly. The Dockerfile does not copy `.env` or `*.json` (except `langgraph.json`) per `.dockerignore`.

---

## Configuration

Create a `.env` file in the project root. Do not commit real keys.


| Variable                         | Required      | Description                                                                                         |
| -------------------------------- | ------------- | --------------------------------------------------------------------------------------------------- |
| `OPENAI_API_KEY`                 | Yes           | OpenAI API key for GPT-4o.                                                                          |
| `GOOGLE_CLOUD_PROJECT`           | Yes           | GCP project ID (e.g. `project-ai-agent-bigquery`).                                                  |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes           | Path to service account JSON key (relative to project root or absolute).                            |
| `BIGQUERY_DB_URI`                | No            | Default `bigquery://bigquery-public-data/new_york_citibike`. Override if using a different dataset. |
| `LANGSMITH_TRACING`              | No            | Set to `true` to enable LangSmith tracing.                                                          |
| `LANGSMITH_API_KEY`              | For LangSmith | LangSmith API key.                                                                                  |
| `LANGSMITH_PROJECT`              | No            | LangSmith project name for organizing traces.                                                       |


**Example `.env` (replace with your values):**

```env
OPENAI_API_KEY=sk-proj-...
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=your-service-account.json

# Optional: LangSmith
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=langgraph-citibike-agent
```

---

## Usage Examples

### 1. Via Streamlit UI

Open `http://localhost:8501` (or your configured port). Type a question or use one of the example questions in the sidebar, e.g.:

- "How many trips are there in total?"
- "What is the most popular route?"
- "What is the average duration?"
- "How many users are subscribers?"
- "Give me the 5 most used stations"
- "Which year has the most trips?"

### 2. Programmatic Usage

```python
from agent import run_agent

response = run_agent("How many trips are in the database?")
print(response)
```

### 3. Example Queries


| Question                           | Expected behavior                                               |
| ---------------------------------- | --------------------------------------------------------------- |
| How many trips are there in total? | `SELECT COUNT(*)` on `citibike_trips`                           |
| What is the most popular route?    | Aggregation on `start_station_name`, `end_station_name`         |
| What is the average duration?      | `AVG(tripduration)` (in seconds; LLM may convert to minutes)    |
| Give me the 5 most used stations   | `GROUP BY start_station_name`, `ORDER BY COUNT(*) DESC LIMIT 5` |


---

## Security and Best Practices

- **Secrets** — `.env` is in `.gitignore` and excluded from the Docker build (`.dockerignore`). Pass secrets at runtime (e.g. `--env-file` for Docker). Never commit API keys or credential files.
- **Credential files** — `*.json` (except `langgraph.json`) is gitignored. Service account JSON keys must not be committed.
- **BigQuery** — The agent queries a public dataset. Ensure your service account has minimal required permissions (e.g. BigQuery Data Viewer). No write access is needed.
- **SQL injection** — The LLM generates SQL; execution is server-side. The `run_sql_query` tool executes whatever the LLM produces. Restrict the service account to read-only access on the target dataset.
- **LangSmith** — If enabled, traces may include prompts and responses. Ensure compliance with your data policies before enabling in production.
- **Streamlit** — The UI has no authentication. If exposed publicly, add a reverse proxy with auth (e.g. nginx, Cloud Run IAM) or restrict network access.

---

## Assumptions and Notes

- The project uses the **BigQuery public dataset** `bigquery-public-data.new_york_citibike.citibike_trips`. No billing is required for querying public datasets, but a GCP project and service account are still needed.
- **LangSmith** is optional and comes as a transitive dependency of `langchain-core`; no explicit package in `requirements.txt`.
- **Streamlit** default port is 8501; the Dockerfile uses 8000 for consistency with common deployment patterns.
- The `build.sh` script uses the directory name as the image name; adjust if your directory name differs from the desired image tag.

