#!/usr/bin/env python
"""
Example 1: Text Messages with from_text()

This example shows how to use canned text messages as a user simulator.
The simulator will send 3 pre-written messages and then end the conversation.

Usage:
    uv run examples/01_text_messages.py
"""

import asyncio

from layercode_gym import LayercodeClient, Settings, UserSimulator


async def main() -> None:
    """Run a simple conversation with 3 canned text messages."""

    # Configure settings (or use environment variables)
    settings = Settings.load()

    # Create simulator with 3 canned messages
    # send_as_text=True means we send text directly (no TTS conversion)
    simulator = UserSimulator.from_text(
        messages=[
            "Hello! I'm interested in learning about your services.",
            "Can you tell me what features are available?",
            "Thank you for the information!",
        ],
        send_as_text=True,  # Send as text, not audio
    )

    # Create client
    client = LayercodeClient(
        simulator=simulator,
        settings=settings,
    )

    # Run the conversation
    print("🎯 Starting conversation with 3 text messages...")
    print("=" * 60)

    conversation_id = await client.run()

    print("=" * 60)
    print("✅ Conversation complete!")
    print(f"📁 Results saved to: {settings.output_root / conversation_id}")
    print(f"💬 Conversation ID: {conversation_id}")


if __name__ == "__main__":
    asyncio.run(main())
