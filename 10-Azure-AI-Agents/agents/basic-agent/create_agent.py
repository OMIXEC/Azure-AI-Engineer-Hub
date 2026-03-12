"""
Basic Agent - Data Analysis with Code Interpreter
==================================================
Enterprise-grade Azure AI Agent that uploads a CSV file and analyzes it
using the Code Interpreter tool. Supports multi-turn conversation.

Requirements:
    - PROJECT_ENDPOINT: Azure AI Foundry project endpoint
      Format: https://{ai-services}.services.ai.azure.com/api/projects/{project}
    - MODEL_DEPLOYMENT_NAME: Name of your deployed model (e.g., gpt-4o)

Auth:
    Uses DefaultAzureCredential. Run `az login` locally, or use managed identity
    in production. No API keys needed.

Usage:
    python create_agent.py
"""

import logging
import os
import sys
from pathlib import Path

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    CodeInterpreterTool,
    FilePurpose,
    ListSortOrder,
    MessageRole,
)
from azure.core.exceptions import AzureError, HttpResponseError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

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
# Configuration
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """Load and validate environment configuration."""
    load_dotenv()
    endpoint = os.getenv("PROJECT_ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME")

    missing = [k for k, v in {"PROJECT_ENDPOINT": endpoint, "MODEL_DEPLOYMENT_NAME": model}.items() if not v]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        logger.error("Copy .env.example to .env and fill in your Azure AI Foundry project values.")
        sys.exit(1)

    return {"endpoint": endpoint, "model": model}


# ---------------------------------------------------------------------------
# Agent helpers
# ---------------------------------------------------------------------------
def create_client(endpoint: str) -> AgentsClient:
    """Create an AgentsClient using DefaultAzureCredential (keyless auth)."""
    credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )
    return AgentsClient(endpoint=endpoint, credential=credential)


def upload_data_file(client: AgentsClient, file_path: Path):
    """Upload a data file for use with CodeInterpreter and return the file object."""
    logger.info("Uploading file: %s", file_path.name)
    try:
        uploaded = client.files.upload_and_poll(
            file_path=file_path,
            purpose=FilePurpose.AGENTS,
        )
        logger.info("File uploaded successfully. ID: %s", uploaded.id)
        return uploaded
    except HttpResponseError as e:
        logger.error(
            "File upload failed. Status: %s | Error: %s | Make sure your PROJECT_ENDPOINT is correct.",
            e.status_code,
            e.message,
        )
        raise


def cleanup(client: AgentsClient, agent_id: str | None, file_id: str | None) -> None:
    """Best-effort cleanup of remote resources."""
    if agent_id:
        try:
            client.delete_agent(agent_id)
            logger.info("Agent deleted: %s", agent_id)
        except AzureError as e:
            logger.warning("Could not delete agent %s: %s", agent_id, e)

    if file_id:
        try:
            client.files.delete(file_id)
            logger.info("File deleted: %s", file_id)
        except AzureError as e:
            logger.warning("Could not delete file %s: %s", file_id, e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    os.system("cls" if os.name == "nt" else "clear")
    config = load_config()

    script_dir = Path(__file__).parent
    data_file = script_dir / "data.txt"

    if not data_file.exists():
        logger.error("Data file not found: %s", data_file)
        sys.exit(1)

    # Display data
    with data_file.open("r") as f:
        content = f.read()
    print("\n--- Data File Contents ---")
    print(content)
    print("--------------------------\n")

    client = create_client(config["endpoint"])

    try:
        with client:
            agent_id: str | None = None
            file_id:  str | None = None
            try:
                # Upload file
                uploaded_file = upload_data_file(client, data_file)
                file_id = uploaded_file.id

                # Build tool
                code_interpreter = CodeInterpreterTool(file_ids=[uploaded_file.id])

                # Create agent
                agent = client.create_agent(
                    model=config["model"],
                    name="data-analysis-agent",
                    instructions=(
                        "You are a precise data analysis agent. "
                        "When given data, use Python (via Code Interpreter) to compute "
                        "statistics, totals, and breakdowns. Present findings clearly."
                    ),
                    tools=code_interpreter.definitions,
                    tool_resources=code_interpreter.resources,
                )
                agent_id = agent.id
                logger.info("Agent created: %s (ID: %s)", agent.name, agent.id)

                # Create conversation thread
                thread = client.threads.create()
                logger.info("Thread created: %s", thread.id)

                print(f"✓ Agent '{agent.name}' ready. Type 'quit' to exit.\n")

                # Conversation loop
                while True:
                    try:
                        user_input = input("You: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\nExiting...")
                        break

                    if user_input.lower() in ("quit", "exit", "q"):
                        break
                    if not user_input:
                        print("Please enter a message.")
                        continue

                    # Send message
                    client.messages.create(
                        thread_id=thread.id,
                        role="user",
                        content=user_input,
                    )

                    # Process run
                    run = client.runs.create_and_process(
                        thread_id=thread.id,
                        agent_id=agent.id,
                    )

                    if run.status == "failed":
                        logger.error("Run failed: %s", run.last_error)
                        print(f"Agent error: {run.last_error}\n")
                        continue

                    # Get latest agent reply
                    last_msg = client.messages.get_last_message_text_by_role(
                        thread_id=thread.id,
                        role=MessageRole.AGENT,
                    )
                    if last_msg:
                        print(f"\nAgent: {last_msg.text.value}\n")

                # Print full conversation log
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

            finally:
                # Cleanup INSIDE `with client:` — transport is still open here
                cleanup(client, agent_id, file_id)

    except HttpResponseError as e:
        logger.error("Azure API error [%s]: %s", e.status_code, e.message)
        if e.status_code == 404:
            logger.error(
                "Resource not found — check that PROJECT_ENDPOINT points to your "
                "Azure AI Foundry project, not the Azure OpenAI endpoint."
            )
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Session interrupted by user.")


if __name__ == "__main__":
    main()

