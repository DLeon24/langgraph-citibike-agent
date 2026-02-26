#!/usr/bin/env python3
"""
Main - Streamlit SQL Agent UI
=============================
Centralized entry point for the CitiBike SQL chat interface.
"""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # Must run before imports that need env vars

from agent import run_agent

PAGE_TITLE = "CitiBike SQL Agent"
PAGE_ICON = "🚴"
CHAT_INPUT_PLACEHOLDER = "Type your question here..."

WELCOME_MESSAGE = """Hi! 👋 I'm your assistant for analyzing CitiBike NYC data.

I can answer questions about:
- 📊 Trip statistics
- 🗺️ Popular routes and stations
- ⏱️ Durations and time patterns
- 👥 User types

**What would you like to know?**"""

RESET_MESSAGE = """Conversation reset! 🔄

What would you like to know about CitiBike data?"""

EXAMPLE_QUESTIONS = [
    "How many trips are there in total?",
    "What is the most popular route?",
    "What is the average duration?",
    "How many users are subscribers?",
    "Give me the 5 most used stations",
    "Which year has the most trips?",
]


def configure_page() -> None:
    """Configures Streamlit page metadata."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_styles() -> None:
    """Renders custom CSS styles."""
    st.markdown(
        """
<style>
    /* Headers - vibrant blue */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0284c7;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #0369a1;
        text-align: center;
        margin-bottom: 2rem;
    }
    /* Chat bubbles - light blue tint, colored border */
    .stChatMessage {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-left: 4px solid #0284c7;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stChatMessage p, .stChatMessage li, .stChatMessage div {
        color: #0c4a6e !important;
    }
    [data-testid="stAppViewContainer"] [data-testid="stChatMessage"] p,
    [data-testid="stAppViewContainer"] [data-testid="stChatMessage"] li {
        color: #0c4a6e !important;
    }
    /* Clear button - blue accent */
    button[kind="secondary"] {
        color: #0369a1 !important;
        border-color: #0284c7 !important;
        background-color: #e0f2fe !important;
    }
    /* Footer - colored strip */
    footer {
        background: linear-gradient(90deg, #e0f2fe, #cffafe) !important;
        padding: 0.75rem !important;
        border-radius: 8px;
    }
    footer p { color: #0369a1 !important; }
</style>
""",
        unsafe_allow_html=True,
    )


def init_session_state() -> None:
    """Initializes required session state values."""
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]

    if "selected_example" not in st.session_state:
        st.session_state.selected_example = None


def render_sidebar() -> None:
    """Renders sidebar with project info, examples, and system status."""
    with st.sidebar:
        st.markdown("## 🚴 CitiBike SQL Agent")
        st.markdown("---")

        st.markdown("### 📊 About this project")
        st.info(
            """
This intelligent agent uses **LangGraph** and **OpenAI** to answer
natural language questions about CitiBike NYC data stored in BigQuery.
"""
        )

        st.markdown("### 💡 Example questions:")
        for example in EXAMPLE_QUESTIONS:
            if st.button(f"📝 {example}", key=example, use_container_width=True):
                st.session_state.selected_example = example

        st.markdown("---")
        st.markdown("### 🛠️ Technologies")
        st.markdown(
            """
- **LangGraph 1.0** - Agent orchestration
- **OpenAI GPT-4o** - Language model
- **BigQuery** - Database
- **Streamlit** - Web interface
"""
        )

        st.markdown("---")
        st.markdown("### ℹ️ System status")

        openai_ok = bool(os.getenv("OPENAI_API_KEY"))
        bigquery_ok = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

        st.markdown(f"**OpenAI:** {'✅' if openai_ok else '❌'}")
        st.markdown(f"**BigQuery:** {'✅' if bigquery_ok else '❌'}")

        if not openai_ok or not bigquery_ok:
            st.error("⚠️ Missing configuration. Check your .env file.")


def render_header() -> None:
    """Renders main header."""
    st.markdown(
        '<p class="main-header">🚴 CitiBike NYC Analyst Agent</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-header">Ask me anything about CitiBike trip data</p>',
        unsafe_allow_html=True,
    )


def render_chat_history() -> None:
    """Displays all chat messages from session state."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def get_prompt() -> str | None:
    """Gets next user prompt from selected example or chat input."""
    if st.session_state.selected_example:
        prompt = st.session_state.selected_example
        st.session_state.selected_example = None
        return prompt

    return st.chat_input(CHAT_INPUT_PLACEHOLDER)


def process_prompt(prompt: str) -> None:
    """Processes a user prompt and appends assistant response."""
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🤔 Analyzing your question and querying BigQuery..."):
            try:
                response = run_agent(prompt)
                st.markdown(response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
            except Exception as e:
                error_msg = (
                    f"❌ **Error:** {e}\n\n"
                    "Please try rephrasing your question or contact the administrator."
                )
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )


def render_clear_button() -> None:
    """Renders clear conversation button."""
    _, center_col, _ = st.columns([1, 1, 1])
    with center_col:
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.messages = [
                {"role": "assistant", "content": RESET_MESSAGE}
            ]
            st.rerun()


def render_footer() -> None:
    """Renders page footer."""
    st.markdown("---")
    st.markdown(
        """
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <p>LangGraph 1.0 + OpenAI GPT-4o + BigQuery</p>
</div>
""",
        unsafe_allow_html=True,
    )


def main() -> None:
    """Main UI orchestrator."""
    configure_page()
    render_styles()
    init_session_state()
    render_sidebar()
    render_header()
    render_chat_history()

    prompt = get_prompt()
    if prompt:
        process_prompt(prompt)

    render_clear_button()
    render_footer()


if __name__ == "__main__":
    main()
