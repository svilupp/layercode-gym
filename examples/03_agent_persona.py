#!/usr/bin/env python
"""
Example 3: AI Agent with Persona using from_agent()

This example shows how to use a PydanticAI agent to simulate a user with a specific persona.
The new from_agent() API dramatically simplifies agent setup with smart defaults.

Two modes demonstrated:
1. Simple mode: Just provide a persona, use all defaults
2. Power user mode: Provide your own custom PydanticAI agent for full control

Usage:
    uv run examples/03_agent_persona.py
"""

import asyncio

from layercode_gym import LayercodeClient, Persona, Settings, UserSimulator


async def main() -> None:
    """Run a conversation with an AI agent simulating a user with a persona."""

    # Configure settings
    settings = Settings.load()

    # Define the user persona - this is all you need!
    persona = Persona(
        background_context=(
            "You are a 35-year-old small business owner who runs a local coffee shop. "
            "You're tech-savvy but busy, and you value efficient, practical solutions. "
            "You're exploring voice AI to improve customer service."
        ),
        intent=(
            "You want to understand how voice AI can help automate customer inquiries "
            "and reduce the workload on your staff during peak hours."
        ),
    )

    # SIMPLE MODE: Create simulator with persona and defaults
    # The from_agent() method automatically:
    # - Creates a default PydanticAI agent (openai:gpt-5-mini)
    # - Loads the prompt template from prompts/basic_agent.txt
    # - Injects persona into the agent's system prompt
    # - Manages conversation history across turns
    # - Auto-creates TTS engine (OpenAI TTS) when send_as_text=False
    simulator = UserSimulator.from_agent(
        persona=persona,
        max_turns=3,  # Have 3 back-and-forth exchanges
        send_as_text=True,  # Use TTS for audio responses (auto-created)
    )

    # POWER USER MODE (commented out - uncomment to use):
    # If you want full control, define your own PydanticAI agent and deps:
    #
    # from pydantic_ai import Agent
    # from layercode_gym import BasicAgentDeps, create_default_deps
    #
    # # Create your custom agent with any model/config
    # my_agent = Agent(
    #     "anthropic:claude-3-5-sonnet",  # Use any model you want
    #     deps_type=BasicAgentDeps,
    # )
    #
    # # Create deps (or define your own deps type!)
    # my_deps = create_default_deps(persona)
    #
    # # Pass your agent and deps directly
    # simulator = UserSimulator.from_agent(
    #     agent=my_agent,
    #     deps=my_deps,
    #     max_turns=3,
    #     send_as_text=False,
    # )

    # Create client and run
    client = LayercodeClient(
        simulator=simulator,
        settings=settings,
    )

    # Run the conversation
    print("🎯 Starting AI-driven conversation with persona...")
    print("=" * 60)
    print(f"👤 Persona: {persona.background_context[:60]}...")
    print(f"🎯 Intent: {persona.intent[:60]}...")
    print("🤖 Agent: OpenAI GPT-5-mini (default)")
    print("🎙️  Audio: TTS auto-generated (OpenAI TTS)")
    print("💬 Max turns: 3")
    print("=" * 60)

    conversation_id = await client.run()

    print("=" * 60)
    print("✅ Conversation complete!")
    print(f"📁 Results saved to: {settings.output_root / conversation_id}")
    print(f"💬 Conversation ID: {conversation_id}")


if __name__ == "__main__":
    asyncio.run(main())
