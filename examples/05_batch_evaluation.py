"""Example 5: Batch Conversation Evaluation

This example demonstrates how to scale evaluations by running multiple
conversations concurrently. This is useful for:
- Load testing your LayerCode agent
- Running regression tests across multiple scenarios
- Bulk evaluation with different user personas

The pattern uses asyncio.gather() with tqdm for progress tracking.
"""

import asyncio
from pathlib import Path

from tqdm.asyncio import tqdm_asyncio

from layercode_gym import LayercodeClient, UserSimulator


async def run_single_conversation(scenario_id: int, message: str) -> tuple[int, str]:
    """Run a single conversation and return its ID and conversation_id.

    Args:
        scenario_id: Unique identifier for this scenario
        message: The message to send

    Returns:
        Tuple of (scenario_id, conversation_id)
    """
    # Create simulator with text-based conversation
    simulator = UserSimulator.from_text(
        messages=[message, "Tell me more.", "Thank you, goodbye."],
        send_as_text=True,  # Use text for faster execution
    )

    # Run conversation
    client = LayercodeClient(simulator=simulator)
    conversation_id = await client.run()

    return scenario_id, conversation_id


async def main() -> None:
    """Run multiple conversations concurrently with progress tracking."""
    # Define test scenarios
    scenarios = [
        "Hello! I'm interested in learning about your services.",
        "Hi there! Can you help me with a question?",
        "Good morning! I'd like to know more about what you offer.",
    ]

    print(f"🚀 Starting batch evaluation with {len(scenarios)} conversations...")
    print("=" * 60)

    # Create tasks for all conversations
    tasks = [run_single_conversation(i, message) for i, message in enumerate(scenarios)]

    # Run all conversations concurrently with progress bar
    results = await tqdm_asyncio.gather(
        *tasks, desc="Running conversations", unit="conversation"
    )

    print("=" * 60)
    print("✅ All conversations complete!")
    print()
    print("📊 Results:")
    for scenario_id, conversation_id in results:
        print(f"   Scenario {scenario_id + 1}: {conversation_id}")

    # Show where results are saved
    conv_root = Path("./conversations")
    print()
    print(f"📁 Results saved to: {conv_root.resolve()}")
    print()
    print("💡 Next steps:")
    print("   - Review transcripts in conversations/<conversation_id>/transcript.json")
    print(
        "   - Listen to audio in conversations/<conversation_id>/conversation_mix.wav"
    )
    print("   - Add callbacks for automated scoring (see example 04)")


if __name__ == "__main__":
    asyncio.run(main())
