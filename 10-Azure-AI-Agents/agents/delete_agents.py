"""
delete_agents.py — Azure AI Foundry Agent Cleanup Utility
==========================================================
Lists all agents in your project and lets you delete them
individually or all at once. Useful for cleaning up orphaned
agents left by crashed or interrupted sessions.

Usage:
    python delete_agents.py           # interactive menu
    python delete_agents.py --all     # delete ALL agents (with confirmation)
    python delete_agents.py --list    # list only, no deletion
"""

import argparse
import logging
import os
import sys

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ListSortOrder
from azure.core.exceptions import AzureError, HttpResponseError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def load_endpoint() -> str:
    load_dotenv()
    ep = os.getenv("PROJECT_ENDPOINT")
    if not ep:
        print("❌  PROJECT_ENDPOINT not set. Copy .env.example → .env and fill in your values.")
        sys.exit(1)
    return ep


def create_client(endpoint: str) -> AgentsClient:
    return AgentsClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        ),
    )


def list_agents(client: AgentsClient) -> list[dict]:
    """Return all agents as a list of dicts."""
    agents = []
    page = client.list_agents(order=ListSortOrder.DESCENDING)
    for agent in page:
        agents.append({"id": agent.id, "name": agent.name or "(unnamed)", "model": agent.model or "?"})
    return agents


def print_agents(agents: list[dict]) -> None:
    if not agents:
        print("\n  ✅  No agents found in this project.\n")
        return
    print(f"\n  {'#':<4} {'Name':<35} {'Model':<20} {'ID'}")
    print("  " + "─" * 90)
    for i, a in enumerate(agents, 1):
        print(f"  {i:<4} {a['name']:<35} {a['model']:<20} {a['id']}")
    print()


def delete_agent_by_id(client: AgentsClient, agent_id: str, name: str) -> bool:
    try:
        client.delete_agent(agent_id)
        print(f"  🗑️  Deleted: {name} ({agent_id})")
        return True
    except HttpResponseError as e:
        print(f"  ❌  Failed to delete {agent_id}: [{e.status_code}] {e.message}")
        return False
    except AzureError as e:
        print(f"  ❌  Azure error deleting {agent_id}: {e}")
        return False


def interactive_menu(client: AgentsClient) -> None:
    """Interactive agent deletion menu."""
    while True:
        agents = list_agents(client)
        print_agents(agents)

        if not agents:
            break

        print("  Options:")
        print("    [1–N]  Delete a specific agent by number")
        print("    [a]    Delete ALL agents")
        print("    [r]    Refresh list")
        print("    [q]    Quit")
        print()

        choice = input("  Your choice: ").strip().lower()

        if choice in ("q", "quit", "exit"):
            break

        if choice == "r":
            continue

        if choice == "a":
            confirm = input(f"\n  ⚠️  Delete ALL {len(agents)} agents? This cannot be undone. [yes/no]: ").strip().lower()
            if confirm == "yes":
                deleted = 0
                for a in agents:
                    if delete_agent_by_id(client, a["id"], a["name"]):
                        deleted += 1
                print(f"\n  ✅  Deleted {deleted}/{len(agents)} agents.\n")
            else:
                print("  Cancelled.\n")
            continue

        # Numeric selection (supports ranges like "1,3,5" or "2-4")
        indices: set[int] = set()
        try:
            for part in choice.split(","):
                part = part.strip()
                if "-" in part and not part.startswith("-"):
                    lo, hi = part.split("-", 1)
                    indices.update(range(int(lo), int(hi) + 1))
                else:
                    indices.add(int(part))
        except ValueError:
            print("  Invalid input. Enter a number, range (e.g. 1-3), or 'a'/'q'.\n")
            continue

        valid = [i for i in indices if 1 <= i <= len(agents)]
        if not valid:
            print("  Number out of range.\n")
            continue

        to_delete = [agents[i - 1] for i in sorted(valid)]
        confirm   = input(
            f"  Delete {len(to_delete)} agent(s): "
            + ", ".join(a["name"] for a in to_delete)
            + "? [y/n]: "
        ).strip().lower()

        if confirm in ("y", "yes"):
            for a in to_delete:
                delete_agent_by_id(client, a["id"], a["name"])
        else:
            print("  Cancelled.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Azure AI Foundry — Agent Cleanup Utility")
    parser.add_argument("--all",  action="store_true", help="Delete all agents without interactive menu")
    parser.add_argument("--list", action="store_true", help="List agents only (no deletion)")
    args = parser.parse_args()

    os.system("cls" if os.name == "nt" else "clear")
    print("═" * 55)
    print("  🛠️   Azure AI Foundry — Agent Cleanup Utility")
    print("═" * 55)

    endpoint = load_endpoint()
    client   = create_client(endpoint)

    try:
        with client:
            agents = list_agents(client)
            print_agents(agents)

            if args.list:
                return

            if not agents:
                return

            if args.all:
                confirm = input(f"  ⚠️  Delete ALL {len(agents)} agents? [yes/no]: ").strip().lower()
                if confirm == "yes":
                    deleted = 0
                    for a in agents:
                        if delete_agent_by_id(client, a["id"], a["name"]):
                            deleted += 1
                    print(f"\n  ✅  Deleted {deleted}/{len(agents)} agents.\n")
                else:
                    print("  Cancelled.")
                return

            # Default: interactive
            interactive_menu(client)

    except HttpResponseError as e:
        print(f"\n❌  Azure API error [{e.status_code}]: {e.message}")
        if e.status_code == 404:
            print("   Check that PROJECT_ENDPOINT is your Azure AI Foundry project endpoint.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Cancelled.")


if __name__ == "__main__":
    main()
