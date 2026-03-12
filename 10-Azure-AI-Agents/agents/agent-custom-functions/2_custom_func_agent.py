"""
Custom Functions Agent — Technical Support (Production Edition)
==============================================================
Azure AI Agent with custom Python function tools for submitting
support tickets. Demonstrates function calling with auto-execution.

Features:
  - Keyless auth via DefaultAzureCredential
  - Structured logging
  - Robust error handling with meaningful messages
  - Proper agent + thread lifecycle management

Requirements:
    PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME in .env
    user_functions.py in the same directory

Usage:
    python 2_custom_func_agent.py
"""

import logging
import os
import sys

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ListSortOrder, MessageRole, ToolSet
from azure.core.exceptions import AzureError, HttpResponseError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from user_functions import user_functions  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_config() -> dict:
    load_dotenv()
    endpoint = os.getenv("PROJECT_ENDPOINT")
    model    = os.getenv("MODEL_DEPLOYMENT_NAME")
    missing  = [k for k, v in {"PROJECT_ENDPOINT": endpoint, "MODEL_DEPLOYMENT_NAME": model}.items() if not v]
    if missing:
        logger.error("Missing required env vars: %s", ", ".join(missing))
        logger.error("Copy .env.example to .env and fill in your Azure AI Foundry details.")
        sys.exit(1)
    return {"endpoint": endpoint, "model": model}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    os.system("cls" if os.name == "nt" else "clear")
    config = load_config()

    credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )
    client = AgentsClient(endpoint=config["endpoint"], credential=credential)

    agent_id: str | None = None

    try:
        with client:
            # Register custom functions
            functions = FunctionTool(user_functions)
            toolset   = ToolSet()
            toolset.add(functions)
            client.enable_auto_function_calls(toolset)

            # Create agent
            agent = client.create_agent(
                model=config["model"],
                name="support-agent",
                instructions=(
                    "You are a technical support agent. "
                    "When a user reports a technical issue, collect their email address "
                    "and a description of the problem. Then call the available function "
                    "to submit a support ticket. Confirm the ticket submission to the user "
                    "and mention any file that was saved."
                ),
                toolset=toolset,
            )
            agent_id = agent.id
            logger.info("Agent created: %s (ID: %s)", agent.name, agent.id)

            thread = client.threads.create()
            logger.info("Thread created: %s", thread.id)
            print(f"\n✓ Connected to '{agent.name}'. Type 'quit' to exit.\n")

            # Conversation loop
            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting…")
                    break

                if user_input.lower() in ("quit", "exit", "q"):
                    break
                if not user_input:
                    print("Please enter a message.")
                    continue

                client.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=user_input,
                )

                run = client.runs.create_and_process(
                    thread_id=thread.id,
                    agent_id=agent.id,
                )

                if run.status == "failed":
                    logger.error("Run failed: %s", run.last_error)
                    print(f"Agent error: {run.last_error}\n")
                    continue

                last = client.messages.get_last_message_text_by_role(
                    thread_id=thread.id,
                    role=MessageRole.AGENT,
                )
                if last:
                    print(f"\nAgent: {last.text.value}\n")

            # Conversation log
            print("\n── Conversation Log ──────────────────────────")
            messages = client.messages.list(
                thread_id=thread.id,
                order=ListSortOrder.ASCENDING,
            )
            for msg in messages:
                if msg.text_messages:
                    role = "You" if msg.role == MessageRole.USER else "Agent"
                    print(f"{role}: {msg.text_messages[-1].text.value}\n")
            print("──────────────────────────────────────────────")

    except HttpResponseError as e:
        logger.error("Azure API error [%s]: %s", e.status_code, e.message)
        if e.status_code == 404:
            logger.error("Check that PROJECT_ENDPOINT is your Azure AI Foundry project endpoint.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.")
    finally:
        if agent_id:
            try:
                client.delete_agent(agent_id)
                logger.info("Agent deleted.")
            except AzureError as e:
                logger.warning("Could not delete agent: %s", e)


if __name__ == "__main__":
    main()
