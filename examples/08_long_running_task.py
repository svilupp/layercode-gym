#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["layercode-gym>=0.1.0"]
# ///
"""
Example: Testing voice agents with long-running tasks.

This example demonstrates both wait features:
1. Wait/Yield: Agent returns WaitForAssistant when assistant says "please wait"
2. Smart Turn-Taking: AI classifier decides when to respond (opt-in)

Use Case:
- Voice agent performs browser automation (30-90 seconds)
- User simulator needs to wait instead of interrupting

Run with:
    uv run python examples/long_running_task.py

Required environment variables (in .env file):
    SERVER_URL=https://your-agent-server.com
    LAYERCODE_AGENT_ID=your_agent_id
    OPENAI_API_KEY=sk-...
"""

import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from layercode_gym import LayercodeClient, UserSimulator, Persona


def log(msg: str) -> None:
    """Print timestamped log message."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


async def on_conversation_end(log_data) -> None:
    """Callback when conversation ends."""
    log(f"Conversation ended: {log_data.conversation_id}")
    log(f"Total turns: {len(log_data.turns)}")

    # Show the conversation
    print("\n" + "=" * 60)
    print("CONVERSATION TRANSCRIPT")
    print("=" * 60)
    for i, turn in enumerate(log_data.turns):
        if turn.assistant_message and turn.assistant_message.content:
            print(f"\n[Turn {i}] ASSISTANT:")
            print(f"  {turn.assistant_message.content[:200]}...")
        if turn.user_message and turn.user_message.content:
            print(f"\n[Turn {i}] USER:")
            print(f"  {turn.user_message.content}")
    print("=" * 60 + "\n")


async def example_with_wait_tool():
    """Example 1: Using Wait/Yield Pattern (enabled by default).

    The agent returns WaitForAssistant when the assistant says
    "please wait" or similar, yielding control until new content arrives.
    """
    log("=" * 60)
    log("EXAMPLE 1: Wait/Yield Pattern (Default Behavior)")
    log("=" * 60)

    # Persona that triggers a long-running task
    simulator = UserSimulator.from_agent(
        persona=Persona(
            background_context="You are a user testing a slow service.",
            intent=(
                "Ask the assistant to help with something. "
                "Be patient and don't interrupt when asked to wait."
            ),
        ),
        max_turns=5,
        send_as_text=True,
        # enable_wait_tool=True is the default
    )

    client = LayercodeClient(
        simulator=simulator,
        conversation_callback=on_conversation_end,
        # Wait up to 5 minutes for long-running tasks
        max_wait_seconds=300.0,
    )

    log("Starting conversation with wait/yield enabled...")
    log("Agent yields when assistant says 'please wait' and resumes with new content.")

    try:
        conversation_id = await client.run()
        log(f"Conversation completed: {conversation_id}")
    except Exception as e:
        log(f"Error: {e}")


async def example_with_smart_turn_taking():
    """Example 2: Using Smart Turn-Taking (opt-in).

    An AI classifier (gpt-5-nano) decides whether to respond or wait,
    checking every ~5 seconds. No persona changes needed.
    """
    log("=" * 60)
    log("EXAMPLE 2: Smart Turn-Taking (Automatic Detection)")
    log("=" * 60)

    # Simple persona - no need to mention waiting
    simulator = UserSimulator.from_agent(
        persona=Persona(
            background_context="You are a user testing a slow service.",
            intent="Ask for help with something. Be patient.",
        ),
        max_turns=3,
        send_as_text=True,
    )

    client = LayercodeClient(
        simulator=simulator,
        conversation_callback=on_conversation_end,
        # Enable smart turn-taking (uses gpt-5-nano classifier)
        enable_smart_turn_taking=True,
    )

    log("Starting conversation with smart turn-taking enabled...")
    log("AI classifier will decide when to respond vs wait.")
    log("Rechecks every ~5 seconds.")

    try:
        conversation_id = await client.run()
        log(f"Conversation completed: {conversation_id}")
    except Exception as e:
        log(f"Error: {e}")


async def example_with_both():
    """Example 3: Using both features (belt and suspenders).

    Combines wait/yield (agent-controlled) with smart turn-taking
    (automatic detection) for maximum reliability.
    """
    log("=" * 60)
    log("EXAMPLE 3: Both Features (Maximum Reliability)")
    log("=" * 60)

    simulator = UserSimulator.from_agent(
        persona=Persona(
            background_context="You are a user testing a slow service.",
            intent="Ask for help. Be patient and don't interrupt when asked to wait.",
        ),
        max_turns=3,
        send_as_text=True,
        enable_wait_tool=True,  # Explicit (default is True)
    )

    client = LayercodeClient(
        simulator=simulator,
        conversation_callback=on_conversation_end,
        enable_smart_turn_taking=True,  # Also use AI classifier
        max_wait_seconds=300.0,
    )

    log("Starting conversation with both features enabled...")
    log("- Wait/yield: Agent yields when asked to wait")
    log("- Smart turn-taking: AI classifier as backup")

    try:
        conversation_id = await client.run()
        log(f"Conversation completed: {conversation_id}")
    except Exception as e:
        log(f"Error: {e}")


async def main():
    """Run the examples."""
    # Check required environment variables
    if not os.getenv("LAYERCODE_AGENT_ID"):
        print("Error: LAYERCODE_AGENT_ID environment variable required")
        print("Set it in .env file or export it")
        return

    print("\n" + "=" * 60)
    print("LONG-RUNNING TASK EXAMPLES")
    print("=" * 60)
    print("""
These examples demonstrate how to test voice agents that perform
long-running tasks (like browser automation) without interrupting them.

Features:
1. Wait/Yield: Agent yields when assistant says "please wait"
2. Smart Turn-Taking: AI classifier decides when to respond

Select an example to run:
  1 - Wait/Yield only (default behavior)
  2 - Smart Turn-Taking only (automatic detection)
  3 - Both features (maximum reliability)
  q - Quit
""")

    choice = input("Enter choice [1/2/3/q]: ").strip().lower()

    if choice == "1":
        await example_with_wait_tool()
    elif choice == "2":
        await example_with_smart_turn_taking()
    elif choice == "3":
        await example_with_both()
    elif choice == "q":
        print("Goodbye!")
    else:
        print("Invalid choice. Running example 1 (wait tool)...")
        await example_with_wait_tool()


if __name__ == "__main__":
    asyncio.run(main())
