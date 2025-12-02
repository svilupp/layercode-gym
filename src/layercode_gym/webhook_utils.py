"""
Webhook management utilities for LayerCode agents.

This is a standalone utility for CI workflows that need to temporarily
update agent webhooks. NOT part of the core gym functionality.

Usage in CI scripts:
    # Save original webhook
    ORIGINAL=$(layercode-gym webhook get --agent-id ag-123 --json | jq -r .webhook_url)

    # Update to PR backend
    layercode-gym webhook update --agent-id ag-123 --url https://pr-456.example.com

    # Run tests
    python run_tests.py

    # Restore original
    layercode-gym webhook update --agent-id ag-123 --url "$ORIGINAL"
"""

import json
import sys
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class AgentInfo:
    """Agent information from LayerCode API."""

    agent_id: str
    webhook_url: str | None
    name: str | None
    raw_data: dict[str, Any]

    def to_json(self) -> str:
        """Convert to JSON string for CLI output."""
        return json.dumps(
            {
                "agent_id": self.agent_id,
                "webhook_url": self.webhook_url,
                "name": self.name,
            },
            indent=2,
        )


def get_agent_webhook(agent_id: str, api_key: str) -> AgentInfo:
    """Get current agent webhook configuration.

    Args:
        agent_id: LayerCode agent ID (e.g., 'ag-123456')
        api_key: LayerCode API key

    Returns:
        AgentInfo with current webhook URL and agent details

    Raises:
        httpx.HTTPError: If API request fails
    """
    url = f"https://api.layercode.com/v1/agents/{agent_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        return AgentInfo(
            agent_id=agent_id,
            webhook_url=data.get("webhook_url"),
            name=data.get("name"),
            raw_data=data,
        )


def update_agent_webhook(agent_id: str, api_key: str, webhook_url: str) -> AgentInfo:
    """Update agent webhook URL.

    Args:
        agent_id: LayerCode agent ID
        api_key: LayerCode API key
        webhook_url: New webhook URL

    Returns:
        Updated AgentInfo

    Raises:
        httpx.HTTPError: If API request fails
    """
    url = f"https://api.layercode.com/v1/agents/{agent_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"webhook_url": webhook_url}

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        return AgentInfo(
            agent_id=agent_id,
            webhook_url=data.get("webhook_url"),
            name=data.get("name"),
            raw_data=data,
        )


def print_agent_info(info: AgentInfo, json_output: bool = False) -> None:
    """Print agent information to stdout.

    Args:
        info: AgentInfo to print
        json_output: If True, output as JSON; otherwise human-readable
    """
    if json_output:
        print(info.to_json())
    else:
        print(f"Agent ID: {info.agent_id}")
        print(f"Name: {info.name or '(not set)'}")
        print(f"Webhook URL: {info.webhook_url or '(not set)'}")


def main_get(
    agent_id: str, api_key: str, json_output: bool = False, ignore_errors: bool = False
) -> int:
    """CLI handler for 'webhook get' command.

    Args:
        agent_id: LayerCode agent ID
        api_key: LayerCode API key
        json_output: Output as JSON if True
        ignore_errors: If True, return 0 even on error (for CI scripts)

    Returns:
        Exit code (0 for success, 1 for error unless ignore_errors=True)
    """
    try:
        info = get_agent_webhook(agent_id, api_key)
        print_agent_info(info, json_output)
        return 0
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("Error: Invalid API key", file=sys.stderr)
        elif e.response.status_code == 404:
            print(f"Error: Agent '{agent_id}' not found", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.response.status_code}", file=sys.stderr)
        return 0 if ignore_errors else 1
    except httpx.HTTPError as e:
        print(f"Error: Network error - {e}", file=sys.stderr)
        return 0 if ignore_errors else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 0 if ignore_errors else 1


def main_update(
    agent_id: str,
    api_key: str,
    webhook_url: str,
    json_output: bool = False,
    ignore_errors: bool = False,
) -> int:
    """CLI handler for 'webhook update' command.

    Args:
        agent_id: LayerCode agent ID
        api_key: LayerCode API key
        webhook_url: New webhook URL
        json_output: Output as JSON if True
        ignore_errors: If True, return 0 even on error (for CI scripts)

    Returns:
        Exit code (0 for success, 1 for error unless ignore_errors=True)
    """
    try:
        info = update_agent_webhook(agent_id, api_key, webhook_url)

        if not json_output:
            print(f"✓ Updated webhook for agent '{agent_id}'")
            print(f"  New URL: {webhook_url}")
        else:
            print_agent_info(info, json_output)

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
                print(f"  {error_data}", file=sys.stderr)
            except Exception:
                pass
        return 0 if ignore_errors else 1
    except httpx.HTTPError as e:
        print(f"Error: Network error - {e}", file=sys.stderr)
        return 0 if ignore_errors else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 0 if ignore_errors else 1
