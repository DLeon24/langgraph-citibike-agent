"""
SQL Data Analyst Agent with LangGraph + BigQuery tool.

This agent:
- Converts natural language questions into BigQuery SQL
- Executes queries through a LangChain tool
- Iterates automatically when SQL errors happen
"""

import os
from typing import Annotated, Literal, Sequence, TypedDict

from dotenv import find_dotenv, load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from tools import run_sql_query

# Search for .env in current and parent directories
load_dotenv(find_dotenv())

# ============================================
# 1. AGENT CONFIGURATION
# ============================================
OPENAI_MODEL = "gpt-4o"
OPENAI_TEMPERATURE = 0
TOOLS = [run_sql_query]

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("❌ Missing OpenAI variable in .env\n" "Required: OPENAI_API_KEY")

# ============================================
# 2. TABLE SCHEMA
# ============================================
TABLE_SCHEMA = """
CREATE TABLE `bigquery-public-data.new_york_citibike.citibike_trips` (
    tripduration INTEGER,
    starttime TIMESTAMP,
    stoptime TIMESTAMP,
    start_station_id INTEGER,
    start_station_name STRING,
    start_station_latitude FLOAT64,
    start_station_longitude FLOAT64,
    end_station_id INTEGER,
    end_station_name STRING,
    end_station_latitude FLOAT64,
    end_station_longitude FLOAT64,
    bikeid INTEGER,
    usertype STRING,
    birth_year INTEGER,
    gender STRING,
    customer_plan STRING
)
"""

# ============================================
# 3. AGENT PROMPT
# ============================================
SYSTEM_PROMPT = f"""
# 🧠 SQL Data Analyst Agent

You are an expert data analyst specialized in writing SQL queries for Google BigQuery.
Your only task is to convert user questions in natural language into precise, functional SQL queries.

## Data Context

You have access to a single table named `bigquery-public-data.new_york_citibike.citibike_trips`.
This is the table schema:

{TABLE_SCHEMA}

## Your Thinking Process

1. **Analyze the User Question**: Understand exactly which metrics, aggregations, filters, and sorting the user is asking for.
2. **Build the SQL Query**: Write a BigQuery SQL query that answers the question.
   - **ALWAYS** use the fully-qualified table name: `bigquery-public-data.new_york_citibike.citibike_trips`.
   - Pay attention to data types. For example, `tripduration` is in seconds.
   - Do not make assumptions. If the question is ambiguous, it is better for the query to fail than to return incorrect data.
3. **Run the Query**: Use the `run_sql_query` tool to execute your SQL.
4. **Interpret the Results**: The tool returns either text data (Markdown) or an error message.
   - If data is returned, present it clearly and answer the original question in natural, friendly language.
   - If an error is returned, analyze it, fix your SQL, and try again. Do not expose raw SQL errors to the user unless you cannot solve the issue. Explain the problem in simple terms.

## Communication Guidelines

- Your final response must be in English.
- Do not tell the user that you are writing SQL. Act like an analyst who simply "finds" the answer.
- If a query returns no results, state it clearly. For example: "I couldn't find trips matching those criteria."
- If the question asks for the "most popular route," assume it refers to the combination of `start_station_name` and `end_station_name`.

Start now.
"""


# ============================================
# 4. GRAPH STATE
# ============================================
class AgentState(TypedDict):
    """State shared between LangGraph nodes."""

    messages: Annotated[Sequence[BaseMessage], add_messages]


# ============================================
# 5. MODEL + GRAPH NODES
# ============================================
def _get_llm_with_tools():
    """Initializes the chat model and binds available tools."""
    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=OPENAI_TEMPERATURE)
    return llm.bind_tools(TOOLS)


LLM_WITH_TOOLS = _get_llm_with_tools()


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Routes to tools if there are tool calls, otherwise ends."""
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return "end"


def call_model(state: AgentState):
    """Calls the LLM; injects system prompt only on first user turn."""
    messages = state["messages"]

    if len(messages) == 1 and isinstance(messages[0], HumanMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = LLM_WITH_TOOLS.invoke(messages)
    return {"messages": [response]}


# ============================================
# 6. BUILD AND EXPORT LANGGRAPH APP
# ============================================
def _build_app():
    """Builds and compiles the LangGraph workflow."""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(TOOLS))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )
    workflow.add_edge("tools", "agent")
    return workflow.compile()


# Exported for LangGraph Studio and app runtime
app = _build_app()


# ============================================
# 7. PUBLIC API
# ============================================
def run_agent(query: str) -> str:
    """
    Runs the SQL analyst agent for a user query.

    Args:
        query: User question in natural language.

    Returns:
        The final assistant response.
    """
    initial_messages = [HumanMessage(content=query)]
    result = app.invoke({"messages": initial_messages})
    return result["messages"][-1].content


# ============================================
# 9. USAGE EXAMPLE
# ============================================

# if __name__ == "__main__":
#     # Verify environment variables are configured
#     if not os.getenv("OPENAI_API_KEY"):
#         print("⚠️  ERROR: OPENAI_API_KEY environment variable is not configured.")
#         print("Please set it with: export OPENAI_API_KEY='your-api-key'")
#         print("Get your API key at: https://platform.openai.com/api-keys")
#         exit(1)

#     # Example questions
#     questions = [
#         "How many total trips are in the database?",
#         "What is the most popular route?",
#         "What is the average trip duration in minutes?"
#     ]

#     print("=" * 80)
#     print("🚴 CITIBIKE ANALYST AGENT WITH LANGGRAPH + OPENAI")
#     print("=" * 80)

#     for i, question in enumerate(questions, 1):
#         print(f"\n{'=' * 80}")
#         print(f"Question {i}: {question}")
#         print(f"{'=' * 80}\n")

#         try:
#             response = run_agent(question)
#             print(f"Response: {response}")
#         except Exception as e:
#             print(f"Error: {e}")

#         print()
