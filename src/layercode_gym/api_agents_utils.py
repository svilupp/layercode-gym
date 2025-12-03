"""
LayerCode Agents REST API utilities.

Direct mapping to the LayerCode REST API for agent management:
- GET /v1/agents/{agent_id} - Get agent details
- POST /v1/agents/{agent_id} - Update agent configuration
- GET /v1/agents - List all agents

Usage in CI scripts:
    # List all agents
    layercode-gym api-agents list --json

    # Get agent details
    layercode-gym api-agents get --agent-id ag-123456

    # Update agent webhook
    layercode-gym api-agents update --agent-id ag-123 --webhook-url https://new.com
"""

import json
import sys
from dataclasses import dataclass
from typing import Any

import httpx

from layercode_gym.logging_utils import sanitize_error


@dataclass
class Agent:
    """Agent information from LayerCode API."""

    agent_id: str
    name: str | None
    webhook_url: str | None
    raw_data: dict[str, Any]

    def to_json(self) -> str:
        """Convert to JSON string for CLI output.

        Returns full config from API for scripting use cases.
        """
        return json.dumps(self.raw_data, indent=2)


def _extract_webhook_url(data: dict[str, Any]) -> str | None:
    """Extract webhook URL from API response.

    The webhook URL is stored at config.endpoint in the LayerCode API.
    """
    config = data.get("config", {})
    return config.get("endpoint") if isinstance(config, dict) else None


def get_agent(agent_id: str, api_key: str) -> Agent:
    """Get agent details.

    Args:
        agent_id: LayerCode agent ID (e.g., 'ag-123456')
        api_key: LayerCode API key

    Returns:
        Agent with current configuration

    Raises:
        httpx.HTTPError: If API request fails
    """
    url = f"https://api.layercode.com/v1/agents/{agent_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        return Agent(
            agent_id=agent_id,
            name=data.get("name"),
            webhook_url=_extract_webhook_url(data),
            raw_data=data,
        )


def update_agent(agent_id: str, api_key: str, update_data: dict[str, Any]) -> Agent:
    """Update agent configuration.

    Args:
        agent_id: LayerCode agent ID
        api_key: LayerCode API key
        update_data: Dict with fields to update (e.g., {"webhook_url": "https://..."})

    Returns:
        Updated Agent

    Raises:
        httpx.HTTPError: If API request fails
    """
    url = f"https://api.layercode.com/v1/agents/{agent_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # API accepts webhook_url at top level for updates
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=update_data)
        response.raise_for_status()
        data = response.json()

        return Agent(
            agent_id=agent_id,
            name=data.get("name"),
            webhook_url=_extract_webhook_url(data),
            raw_data=data,
        )


def list_agents(api_key: str) -> list[Agent]:
    """List all agents in your account.

    Args:
        api_key: LayerCode API key

    Returns:
        List of Agents

    Raises:
        httpx.HTTPError: If API request fails
    """
    url = "https://api.layercode.com/v1/agents"
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Handle both array response and object with 'agents' key
        agents_data = data if isinstance(data, list) else data.get("agents", [])

        return [
            Agent(
                agent_id=agent.get("agent_id", agent.get("id", "")),
                name=agent.get("name"),
                webhook_url=_extract_webhook_url(agent),
                raw_data=agent,
            )
            for agent in agents_data
        ]


def print_agent(agent: Agent, json_output: bool = False) -> None:
    """Print agent information to stdout.

    Args:
        agent: Agent to print
        json_output: If True, output as JSON; otherwise human-readable
    """
    if json_output:
        print(agent.to_json())
    else:
        print(f"Agent ID: {agent.agent_id}")
        print(f"Name: {agent.name or '(not set)'}")
        print(f"Webhook URL: {agent.webhook_url or '(not set)'}")
        print(
            "\nTip: Use --json for full pipeline config (voice, transcription, speech, etc.)"
        )


def print_agents(agents: list[Agent], json_output: bool = False) -> None:
    """Print list of agents to stdout.

    Args:
        agents: List of agents to print
        json_output: If True, output as JSON; otherwise human-readable
    """
    if json_output:
        agents_data = [
            {
                "agent_id": a.agent_id,
                "name": a.name,
            }
            for a in agents
        ]
        print(json.dumps(agents_data, indent=2))
    else:
        if not agents:
            print("No agents found")
            return

        print(f"Found {len(agents)} agent(s):\n")
        for i, agent in enumerate(agents, 1):
            print(f"{i}. {agent.name or 'Unnamed Agent'} ({agent.agent_id})")
        print("\nTip: Use 'api-agents get --agent-id <id>' to see webhook URL")


def main_get(agent_id: str, api_key: str, json_output: bool = False) -> int:
    """CLI handler for 'api-agents get' command.

    Args:
        agent_id: LayerCode agent ID
        api_key: LayerCode API key
        json_output: Output as JSON if True

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        agent = get_agent(agent_id, api_key)
        print_agent(agent, json_output)
        return 0
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("Error: Invalid API key", file=sys.stderr)
        elif e.response.status_code == 404:
            print(f"Error: Agent '{agent_id}' not found", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.response.status_code}", file=sys.stderr)
        return 1
    except httpx.HTTPError as e:
        print(f"Error: Network error - {sanitize_error(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {sanitize_error(e)}", file=sys.stderr)
        return 1


def main_update(
    agent_id: str, api_key: str, update_data: dict[str, Any], json_output: bool = False
) -> int:
    """CLI handler for 'api-agents update' command.

    Args:
        agent_id: LayerCode agent ID
        api_key: LayerCode API key
        update_data: Dict with fields to update
        json_output: Output as JSON if True

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        agent = update_agent(agent_id, api_key, update_data)

        if not json_output:
            print(f"✓ Updated agent '{agent_id}'")
            for key, value in update_data.items():
                print(f"  {key}: {value}")
        else:
            print_agent(agent, json_output)

        return 0
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("Error: Invalid API key", file=sys.stderr)
        elif e.response.status_code == 404:
            print(f"Error: Agent '{agent_id}' not found", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.response.status_code}", file=sys.stderr)
            try:
                error_data = e.response.json()
                # Sanitize error response in case it contains sensitive info
                print(f"  {sanitize_error(str(error_data))}", file=sys.stderr)
            except Exception:
                pass
        return 1
    except httpx.HTTPError as e:
        print(f"Error: Network error - {sanitize_error(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {sanitize_error(e)}", file=sys.stderr)
        return 1


def main_list(api_key: str, json_output: bool = False) -> int:
    """CLI handler for 'api-agents list' command.

    Args:
        api_key: LayerCode API key
        json_output: Output as JSON if True

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        agents = list_agents(api_key)
        print_agents(agents, json_output)
        return 0
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("Error: Invalid API key", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.response.status_code}", file=sys.stderr)
        return 1
    except httpx.HTTPError as e:
        print(f"Error: Network error - {sanitize_error(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {sanitize_error(e)}", file=sys.stderr)
        return 1
