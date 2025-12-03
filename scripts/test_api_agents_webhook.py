#!/usr/bin/env python3
"""Test script to verify api-agents webhook update works correctly.

Usage:
    LAYERCODE_API_KEY=... LAYERCODE_AGENT_ID=... uv run scripts/test_api_agents_webhook.py

This script:
1. Gets the current webhook URL
2. Sets a test webhook URL
3. Gets to verify it was updated
4. Restores the original webhook URL
5. Gets to verify restoration worked
"""

import os
import sys

from layercode_gym.api_agents_utils import get_agent, update_agent


def main() -> int:
    agent_id = os.environ.get("LAYERCODE_AGENT_ID")
    api_key = os.environ.get("LAYERCODE_API_KEY")

    if not agent_id:
        print("Error: LAYERCODE_AGENT_ID environment variable required")
        return 1

    if not api_key:
        print("Error: LAYERCODE_API_KEY environment variable required")
        return 1

    test_url = "https://test-webhook-update.example.com/api/test"

    print(f"Testing webhook update for agent: {agent_id}\n")

    # Step 1: Get current webhook
    print("1. Getting current webhook URL...")
    agent = get_agent(agent_id, api_key)
    original_url = agent.webhook_url
    print(f"   Current: {original_url or '(not set)'}\n")

    # Step 2: Set test webhook
    print(f"2. Setting test webhook URL: {test_url}")
    updated = update_agent(agent_id, api_key, {"webhook_url": test_url})
    print(f"   Response: {updated.webhook_url}\n")

    # Step 3: Verify update
    print("3. Verifying update...")
    verified = get_agent(agent_id, api_key)
    if verified.webhook_url == test_url:
        print(f"   OK: Webhook updated to {verified.webhook_url}\n")
    else:
        print(f"   FAIL: Expected {test_url}, got {verified.webhook_url}")
        return 1

    # Step 4: Restore original
    print(f"4. Restoring original webhook: {original_url or '(not set)'}")
    if original_url:
        restored = update_agent(agent_id, api_key, {"webhook_url": original_url})
        print(f"   Response: {restored.webhook_url}\n")
    else:
        print("   Skipping restore (original was not set)\n")

    # Step 5: Verify restoration
    print("5. Verifying restoration...")
    final = get_agent(agent_id, api_key)
    if final.webhook_url == original_url:
        print(f"   OK: Webhook restored to {final.webhook_url or '(not set)'}\n")
    else:
        print(f"   FAIL: Expected {original_url}, got {final.webhook_url}")
        return 1

    print("All tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
